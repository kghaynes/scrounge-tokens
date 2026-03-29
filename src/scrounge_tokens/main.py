#!/usr/bin/env python3
"""scrounge-tokens: Fetch and display AI model pricing from providers."""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Source: litellm community-maintained pricing database
PRICING_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

# litellm provider keys -> display names
# Note: Google uses "gemini" as its provider key (not "google").
# Note: "nvidia_nim" exists in litellm but currently only contains rerank models
#       with no pricing — NVIDIA NIM chat model pricing is not yet in this source.
PROVIDERS = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "gemini": "Google",
    "nvidia_nim": "NVIDIA",
}

# Prefixes to strip from model keys for cleaner display
STRIP_PREFIXES = ("gemini/", "nvidia_nim/")

# Matches date/version suffixes to collapse model variants:
#   -20241022          YYYYMMDD  (Anthropic, OpenAI)
#   -2024-08-06        YYYY-MM-DD (OpenAI)
#   -09-2025           MM-YYYY   (Google preview dates)
#   -06-17             MM-DD     (Google preview dates)
#   -001               NNN       (Google point versions)
_DATE_SUFFIX = re.compile(r"-(\d{8}|\d{4}-\d{2}-\d{2}|\d{2}-\d{4}|\d{2}-\d{2}|\d{3})$")

# Only include models with these modes (or no mode specified)
CHAT_MODES = {"chat", "completion", None}

CACHE_PATH = Path.home() / ".cache" / "scrounge-tokens" / "prices.json"

# Specialized model categories — hidden by default
_SPECIALIZED_TERMS = ("audio", "realtime", "search", "robotics", "computer-use", "tts", "customtools")

# Deprecated model families — hidden by default
_DEPRECATED_PREFIXES = ("gpt-3.5", "gemini-exp")
_DEPRECATED_NAMES = frozenset({
    "gpt-4",
    "gpt-4-0314",
    "gpt-4-0613",
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-4-1106-preview",
    "gpt-4-0125-preview",
    "gpt-3.5-turbo-16k",
})

# Alias/pointer models — hidden by default
# -latest: API aliases that always point to the current version
# -chat:   alternate ChatGPT-style endpoints (gpt-5-chat, gpt-5-chat-latest)
# base names: Anthropic publishes the same model under two naming conventions
#   claude-4-sonnet-* == claude-sonnet-4-*
#   claude-4-opus-*   == claude-opus-4-*
_ALIAS_SUFFIXES = ("-latest",)
_ALIAS_SUBSTRINGS = ("-chat",)
_ALIAS_BASE_NAMES = frozenset({
    "claude-4-sonnet",
    "claude-4-opus",
})


def fetch_pricing() -> dict:
    response = httpx.get(PRICING_URL, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_models(data: dict) -> list[dict]:
    models = []
    for model_key, info in data.items():
        if not isinstance(info, dict):
            continue

        provider = info.get("litellm_provider", "")
        if provider not in PROVIDERS:
            continue

        # Skip non-chat models (embeddings, image gen, etc.)
        if info.get("mode") not in CHAT_MODES:
            continue

        input_cost = info.get("input_cost_per_token")
        output_cost = info.get("output_cost_per_token")

        # Skip models with no pricing (None or explicit 0)
        if not (input_cost or output_cost):
            continue

        context_tokens = info.get("max_input_tokens") or info.get("max_tokens")

        models.append(
            {
                "provider": PROVIDERS[provider],
                "model": _strip_prefix(model_key),
                "input_per_1m": input_cost * 1_000_000 if input_cost else None,
                "output_per_1m": output_cost * 1_000_000 if output_cost else None,
                "context_tokens": context_tokens,
                "context": _format_context(context_tokens),
                "vision": "Y" if info.get("supports_vision") else "N",
                "tools": "Y" if info.get("supports_function_calling") else "N",
            }
        )

    models.sort(key=lambda m: (m["provider"], m["model"]))
    return models


def filter_models(
    models: list[dict],
    provider: str | None = None,
    min_context: int | None = None,
    max_cost: float | None = None,
) -> list[dict]:
    if provider:
        models = [m for m in models if m["provider"].lower() == provider.lower()]
    if min_context is not None:
        models = [m for m in models if (m.get("context_tokens") or 0) >= min_context]
    if max_cost is not None:
        models = [
            m for m in models if m["input_per_1m"] is not None and m["input_per_1m"] <= max_cost
        ]
    return models


def sort_models(models: list[dict], sort_by: str = "provider") -> list[dict]:
    sort_keys: dict = {
        "input-cost": lambda m: (m["input_per_1m"] if m["input_per_1m"] is not None else float("inf")),
        "output-cost": lambda m: (m["output_per_1m"] if m["output_per_1m"] is not None else float("inf")),
        "context": lambda m: -(m.get("context_tokens") or 0),  # largest first
        "model": lambda m: m["model"],
        "provider": lambda m: (m["provider"], m["model"]),
    }
    return sorted(models, key=sort_keys.get(sort_by, sort_keys["provider"]))


def deduplicate_models(models: list[dict]) -> list[dict]:
    """Collapse dated version variants, keeping one representative per model family.

    Prefers the canonical unversioned name (e.g. 'gpt-4o') over dated variants
    (e.g. 'gpt-4o-2024-11-20'). When no canonical exists, keeps the latest date.
    Matches suffixes like -20241022 or -2024-08-06.
    """
    seen: dict[tuple, dict] = {}
    for model in models:
        key = (model["provider"], _base_name(model["model"]))
        if key not in seen:
            seen[key] = model
        else:
            existing = seen[key]
            current_is_canonical = model["model"] == _base_name(model["model"])
            existing_is_canonical = existing["model"] == _base_name(existing["model"])
            if current_is_canonical and not existing_is_canonical:
                seen[key] = model  # promote canonical over dated variant
            elif not existing_is_canonical and model["model"] > existing["model"]:
                seen[key] = model  # keep later dated variant
    return list(seen.values())


def add_estimated_cost(models: list[dict], input_tokens: int, output_tokens: int) -> list[dict]:
    for model in models:
        in_cost = (model["input_per_1m"] or 0) * input_tokens / 1_000_000
        out_cost = (model["output_per_1m"] or 0) * output_tokens / 1_000_000
        model["est_cost"] = in_cost + out_cost
    return models


def load_cache() -> dict | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return None


def save_cache(models: list[dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
    }
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def apply_price_changes(current: list[dict], cached_models: list[dict]) -> list[dict]:
    """Compare current models against cached models and annotate with price changes."""
    prev = {f"{m['provider']}|{m['model']}": m for m in cached_models}
    for model in current:
        key = f"{model['provider']}|{model['model']}"
        if key not in prev:
            model["input_change"] = "new"
            model["output_change"] = "new"
        else:
            model["input_change"] = _price_delta(
                model["input_per_1m"], prev[key].get("input_per_1m")
            )
            model["output_change"] = _price_delta(
                model["output_per_1m"], prev[key].get("output_per_1m")
            )
    return current


def print_table(
    models: list[dict], show_changes: bool = False, show_est_cost: bool = False
) -> None:
    if not models:
        print("No models found.", file=sys.stderr)
        return

    headers = ["Provider", "Model", "Input $/1M", "Output $/1M", "Context", "Vision", "Tools"]
    if show_changes:
        headers += ["Input Chg", "Output Chg"]
    if show_est_cost:
        headers.append("Est. Cost")

    rows = []
    for m in models:
        row = [
            m["provider"],
            m["model"],
            _format_cost(m["input_per_1m"]),
            _format_cost(m["output_per_1m"]),
            m.get("context", "-"),
            m.get("vision", "-"),
            m.get("tools", "-"),
        ]
        if show_changes:
            row.append(m.get("input_change") or "-")
            row.append(m.get("output_change") or "-")
        if show_est_cost:
            row.append(f"${m['est_cost']:.4f}")
        rows.append(row)

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    separator = "-+-".join("-" * w for w in col_widths)
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))

    print(header_line)
    print(separator)
    for row in rows:
        print(" | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)))

    print(f"\n{len(models)} models")


def print_json_output(models: list[dict]) -> None:
    output = [{k: v for k, v in m.items() if k != "context_tokens"} for m in models]
    print(json.dumps(output, indent=2))


def print_csv_output(models: list[dict]) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(["provider", "model", "input_per_1m", "output_per_1m", "context", "vision", "tools"])
    for m in models:
        writer.writerow([
            m["provider"],
            m["model"],
            m["input_per_1m"],
            m["output_per_1m"],
            m.get("context", ""),
            m.get("vision", ""),
            m.get("tools", ""),
        ])


def _is_ft(model: dict) -> bool:
    """Fine-tuned model (prefixed with ft:)."""
    return model["model"].startswith("ft:")


def _is_specialized(model_name: str) -> bool:
    """Audio, realtime, or search-specific model."""
    lower = model_name.lower()
    return any(t in lower for t in _SPECIALIZED_TERMS)


def _is_deprecated(model_name: str) -> bool:
    """Old model generation superseded by cheaper/better alternatives."""
    if model_name in _DEPRECATED_NAMES:
        return True
    return any(model_name.startswith(p) for p in _DEPRECATED_PREFIXES)


def _is_alias(model_name: str) -> bool:
    """Pointer aliases, alternate endpoints, or cross-named duplicates."""
    if any(model_name.endswith(s) for s in _ALIAS_SUFFIXES):
        return True
    if any(s in model_name for s in _ALIAS_SUBSTRINGS):
        return True
    return _base_name(model_name) in _ALIAS_BASE_NAMES


def _base_name(model_name: str) -> str:
    """Strip a date-based version suffix from a model name."""
    return _DATE_SUFFIX.sub("", model_name)


def _strip_prefix(model_key: str) -> str:
    for prefix in STRIP_PREFIXES:
        if model_key.startswith(prefix):
            return model_key[len(prefix):]
    return model_key


def _format_context(tokens: int | None) -> str:
    if tokens is None:
        return "-"
    if tokens >= 1_000_000:
        return f"{tokens // 1_000_000}M"
    if tokens >= 1_000:
        return f"{tokens // 1_000}K"
    return str(tokens)


def _format_cost(cost: float | None) -> str:
    if cost is None:
        return "-"
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"


def _price_delta(current: float | None, previous: float | None) -> str | None:
    if current is None or previous is None:
        return None
    delta = current - previous
    if abs(delta) < 0.0001:
        return None
    sign = "+" if delta > 0 else "-"
    return f"{sign}{_format_cost(abs(delta))}"


def _parse_token_count(value: str) -> int:
    """Parse token counts like '128k', '1.5m', '1000000'."""
    v = value.lower().strip()
    if v.endswith("m"):
        return int(float(v[:-1]) * 1_000_000)
    if v.endswith("k"):
        return int(float(v[:-1]) * 1_000)
    return int(v)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and display AI model pricing from providers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  scrounge-tokens                                        show all models
  scrounge-tokens --provider anthropic                   Anthropic only
  scrounge-tokens --min-context 128k                     128K+ context only
  scrounge-tokens --max-cost 5                           under $5/1M input tokens
  scrounge-tokens --sort-by input-cost                   cheapest first
  scrounge-tokens --input-tokens 1m --output-tokens 100k estimate costs
  scrounge-tokens --json                                 JSON output
  scrounge-tokens --csv                                  CSV output
  scrounge-tokens --cached                               use cached data (offline)
  scrounge-tokens --all-versions                         show all dated variants
        """,
    )
    parser.add_argument(
        "--provider",
        help="Filter by provider (anthropic, openai, google, nvidia)",
    )
    parser.add_argument(
        "--min-context",
        metavar="SIZE",
        help="Minimum context window, e.g. 128k, 1m",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        metavar="DOLLARS",
        help="Maximum input cost per 1M tokens (dollars)",
    )
    parser.add_argument(
        "--sort-by",
        default="provider",
        choices=["provider", "input-cost", "output-cost", "context", "model"],
        help="Sort field (default: provider)",
    )
    parser.add_argument(
        "--input-tokens",
        metavar="COUNT",
        help="Estimate cost for this many input tokens, e.g. 1m, 500k",
    )
    parser.add_argument(
        "--output-tokens",
        metavar="COUNT",
        help="Estimate cost for this many output tokens, e.g. 100k",
    )
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output as JSON")
    parser.add_argument("--csv", action="store_true", dest="output_csv", help="Output as CSV")
    parser.add_argument(
        "--cached",
        action="store_true",
        help="Use cached pricing data instead of fetching",
    )
    parser.add_argument(
        "--all-versions",
        action="store_true",
        help="Show all dated model versions (default: collapse to one per family)",
    )
    parser.add_argument(
        "--show-ft",
        action="store_true",
        help="Include fine-tuned models (ft:*) — hidden by default",
    )
    parser.add_argument(
        "--show-specialized",
        action="store_true",
        help="Include audio, realtime, and search models — hidden by default",
    )
    parser.add_argument(
        "--show-deprecated",
        action="store_true",
        help="Include deprecated model generations (GPT-3.5, old GPT-4) — hidden by default",
    )
    parser.add_argument(
        "--show-aliases",
        action="store_true",
        help="Include -latest pointers, -chat endpoints, and cross-named duplicates — hidden by default",
    )
    args = parser.parse_args()

    cache = load_cache()

    if args.cached:
        if not cache:
            print("No cached data found. Run without --cached to fetch first.", file=sys.stderr)
            sys.exit(1)
        models = cache["models"]
        fetched_at = cache.get("fetched_at", "unknown time")
        print(f"Using cached data from {fetched_at}", file=sys.stderr)
    else:
        try:
            data = fetch_pricing()
        except httpx.HTTPError as e:
            print(f"Error fetching pricing data: {e}", file=sys.stderr)
            if cache:
                print("Tip: run with --cached to use last saved data.", file=sys.stderr)
            sys.exit(1)

        models = parse_models(data)
        save_cache(models)

    # Price change detection — only on fresh fetch when a prior cache exists
    show_changes = False
    if not args.cached and cache:
        models = apply_price_changes(models, cache["models"])
        show_changes = any(m.get("input_change") or m.get("output_change") for m in models)

    # Deduplication (collapse dated version variants by default)
    if not args.all_versions:
        models = deduplicate_models(models)

    # Default exclusions (opt in with --show-* flags)
    if not args.show_ft:
        models = [m for m in models if not _is_ft(m)]
    if not args.show_specialized:
        models = [m for m in models if not _is_specialized(m["model"])]
    if not args.show_deprecated:
        models = [m for m in models if not _is_deprecated(m["model"])]
    if not args.show_aliases:
        models = [m for m in models if not _is_alias(m["model"])]

    # Filters and sort
    min_context = _parse_token_count(args.min_context) if args.min_context else None
    models = filter_models(models, args.provider, min_context, args.max_cost)
    models = sort_models(models, args.sort_by)

    # Cost estimation
    show_est_cost = False
    if args.input_tokens or args.output_tokens:
        in_tokens = _parse_token_count(args.input_tokens) if args.input_tokens else 0
        out_tokens = _parse_token_count(args.output_tokens) if args.output_tokens else 0
        models = add_estimated_cost(models, in_tokens, out_tokens)
        show_est_cost = True

    if args.output_json:
        print_json_output(models)
    elif args.output_csv:
        print_csv_output(models)
    else:
        print_table(models, show_changes=show_changes, show_est_cost=show_est_cost)


if __name__ == "__main__":
    main()
