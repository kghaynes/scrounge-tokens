#!/usr/bin/env python3
"""scrounge-tokens: Fetch and display AI model pricing from providers."""

import sys

import httpx

# Source: litellm community-maintained pricing database
PRICING_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

# litellm provider keys -> display names
PROVIDERS = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "google": "Google",
    "nvidia_nim": "NVIDIA",
}

# Prefixes to strip from model keys for cleaner display
STRIP_PREFIXES = ("gemini/", "nvidia_nim/")

# Only include models with these modes (or no mode specified)
CHAT_MODES = {"chat", "completion", None}


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

        # Skip models with no pricing info at all
        if input_cost is None and output_cost is None:
            continue

        context_tokens = info.get("max_input_tokens") or info.get("max_tokens")

        models.append(
            {
                "provider": PROVIDERS[provider],
                "model": _strip_prefix(model_key),
                "input_per_1m": input_cost * 1_000_000 if input_cost else None,
                "output_per_1m": output_cost * 1_000_000 if output_cost else None,
                "context": _format_context(context_tokens),
            }
        )

    models.sort(key=lambda m: (m["provider"], m["model"]))
    return models


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


def print_table(models: list[dict]) -> None:
    if not models:
        print("No models found.", file=sys.stderr)
        return

    headers = ["Provider", "Model", "Input $/1M", "Output $/1M", "Context"]
    rows = [
        [
            m["provider"],
            m["model"],
            _format_cost(m["input_per_1m"]),
            _format_cost(m["output_per_1m"]),
            m["context"],
        ]
        for m in models
    ]

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


def main() -> None:
    try:
        data = fetch_pricing()
    except httpx.HTTPError as e:
        print(f"Error fetching pricing data: {e}", file=sys.stderr)
        sys.exit(1)

    models = parse_models(data)
    print_table(models)


if __name__ == "__main__":
    main()
