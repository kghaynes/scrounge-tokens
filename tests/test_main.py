"""Tests for scrounge_tokens.main."""

import pytest

from scrounge_tokens.main import (
    _format_context,
    _format_cost,
    _parse_token_count,
    _price_delta,
    _strip_prefix,
    add_estimated_cost,
    apply_price_changes,
    filter_models,
    parse_models,
    print_table,
    sort_models,
)


# --- _format_context ---


def test_format_context_none():
    assert _format_context(None) == "-"


def test_format_context_thousands():
    assert _format_context(128_000) == "128K"


def test_format_context_millions():
    assert _format_context(1_000_000) == "1M"


def test_format_context_small():
    assert _format_context(512) == "512"


# --- _format_cost ---


def test_format_cost_none():
    assert _format_cost(None) == "-"


def test_format_cost_dollars():
    assert _format_cost(15.0) == "$15.00"


def test_format_cost_sub_cent():
    assert _format_cost(0.000003) == "$0.0000"


def test_format_cost_fractional():
    assert _format_cost(3.0) == "$3.00"


# --- _strip_prefix ---


def test_strip_prefix_gemini():
    assert _strip_prefix("gemini/gemini-1.5-pro") == "gemini-1.5-pro"


def test_strip_prefix_nvidia():
    assert _strip_prefix("nvidia_nim/meta/llama-3.1-8b-instruct") == "meta/llama-3.1-8b-instruct"


def test_strip_prefix_no_match():
    assert _strip_prefix("claude-opus-4-5") == "claude-opus-4-5"


# --- _parse_token_count ---


def test_parse_token_count_k():
    assert _parse_token_count("128k") == 128_000


def test_parse_token_count_K_uppercase():
    assert _parse_token_count("128K") == 128_000


def test_parse_token_count_m():
    assert _parse_token_count("1m") == 1_000_000


def test_parse_token_count_decimal():
    assert _parse_token_count("1.5m") == 1_500_000


def test_parse_token_count_raw():
    assert _parse_token_count("200000") == 200_000


# --- _price_delta ---


def test_price_delta_increase():
    assert _price_delta(5.0, 3.0) == "+$2.00"


def test_price_delta_decrease():
    assert _price_delta(3.0, 5.0) == "-$2.00"


def test_price_delta_no_change():
    assert _price_delta(3.0, 3.0) is None


def test_price_delta_none_current():
    assert _price_delta(None, 3.0) is None


def test_price_delta_none_previous():
    assert _price_delta(3.0, None) is None


# --- Sample data ---

SAMPLE_DATA = {
    "claude-3-5-sonnet-20241022": {
        "litellm_provider": "anthropic",
        "mode": "chat",
        "input_cost_per_token": 0.000003,
        "output_cost_per_token": 0.000015,
        "max_input_tokens": 200_000,
        "supports_vision": True,
        "supports_function_calling": True,
    },
    "gpt-4o": {
        "litellm_provider": "openai",
        "mode": "chat",
        "input_cost_per_token": 0.0000025,
        "output_cost_per_token": 0.00001,
        "max_input_tokens": 128_000,
        "supports_vision": True,
        "supports_function_calling": True,
    },
    "gemini/gemini-1.5-pro": {
        "litellm_provider": "google",
        "mode": "chat",
        "input_cost_per_token": 0.00000125,
        "output_cost_per_token": 0.000005,
        "max_input_tokens": 2_000_000,
        "supports_vision": True,
        "supports_function_calling": True,
    },
    "nvidia_nim/meta/llama-3.1-8b-instruct": {
        "litellm_provider": "nvidia_nim",
        "mode": "chat",
        "input_cost_per_token": 0.0000001,
        "output_cost_per_token": 0.0000001,
        "max_input_tokens": 128_000,
        "supports_vision": False,
        "supports_function_calling": False,
    },
    # Should be excluded: embedding mode
    "text-embedding-3-small": {
        "litellm_provider": "openai",
        "mode": "embedding",
        "input_cost_per_token": 0.00000002,
        "output_cost_per_token": None,
        "max_input_tokens": 8_191,
    },
    # Should be excluded: unknown provider
    "some-unknown-model": {
        "litellm_provider": "unknown_provider",
        "mode": "chat",
        "input_cost_per_token": 0.000001,
        "output_cost_per_token": 0.000002,
    },
    # Should be excluded: no pricing
    "free-model": {
        "litellm_provider": "anthropic",
        "mode": "chat",
        "input_cost_per_token": None,
        "output_cost_per_token": None,
    },
}


# --- parse_models ---


def test_parse_models_count():
    models = parse_models(SAMPLE_DATA)
    assert len(models) == 4


def test_parse_models_excludes_embeddings():
    models = parse_models(SAMPLE_DATA)
    assert "text-embedding-3-small" not in [m["model"] for m in models]


def test_parse_models_excludes_unknown_provider():
    models = parse_models(SAMPLE_DATA)
    assert "unknown_provider" not in {m["provider"] for m in models}


def test_parse_models_excludes_no_pricing():
    models = parse_models(SAMPLE_DATA)
    assert "free-model" not in [m["model"] for m in models]


def test_parse_models_strips_gemini_prefix():
    models = parse_models(SAMPLE_DATA)
    assert "gemini-1.5-pro" in [m["model"] for m in models]


def test_parse_models_strips_nvidia_prefix():
    models = parse_models(SAMPLE_DATA)
    assert "meta/llama-3.1-8b-instruct" in [m["model"] for m in models]


def test_parse_models_cost_conversion():
    models = parse_models(SAMPLE_DATA)
    claude = next(m for m in models if m["model"] == "claude-3-5-sonnet-20241022")
    assert claude["input_per_1m"] == pytest.approx(3.0)
    assert claude["output_per_1m"] == pytest.approx(15.0)


def test_parse_models_vision_flag():
    models = parse_models(SAMPLE_DATA)
    claude = next(m for m in models if m["model"] == "claude-3-5-sonnet-20241022")
    assert claude["vision"] == "Y"
    nvidia = next(m for m in models if "llama" in m["model"])
    assert nvidia["vision"] == "N"


def test_parse_models_tools_flag():
    models = parse_models(SAMPLE_DATA)
    gpt = next(m for m in models if m["model"] == "gpt-4o")
    assert gpt["tools"] == "Y"
    nvidia = next(m for m in models if "llama" in m["model"])
    assert nvidia["tools"] == "N"


def test_parse_models_sorted():
    models = parse_models(SAMPLE_DATA)
    providers = [m["provider"] for m in models]
    assert providers == sorted(providers)


# --- filter_models ---


def test_filter_by_provider():
    models = parse_models(SAMPLE_DATA)
    filtered = filter_models(models, provider="anthropic")
    assert all(m["provider"] == "Anthropic" for m in filtered)
    assert len(filtered) == 1


def test_filter_by_provider_case_insensitive():
    models = parse_models(SAMPLE_DATA)
    filtered = filter_models(models, provider="OPENAI")
    assert all(m["provider"] == "OpenAI" for m in filtered)


def test_filter_by_min_context():
    models = parse_models(SAMPLE_DATA)
    filtered = filter_models(models, min_context=500_000)
    # Only gemini-1.5-pro has 2M context
    assert len(filtered) == 1
    assert filtered[0]["model"] == "gemini-1.5-pro"


def test_filter_by_max_cost():
    models = parse_models(SAMPLE_DATA)
    filtered = filter_models(models, max_cost=1.0)
    # Only NVIDIA model is under $1/1M
    assert len(filtered) == 1
    assert "llama" in filtered[0]["model"]


def test_filter_no_criteria_returns_all():
    models = parse_models(SAMPLE_DATA)
    assert filter_models(models) == models


# --- sort_models ---


def test_sort_by_input_cost():
    models = parse_models(SAMPLE_DATA)
    sorted_models = sort_models(models, "input-cost")
    costs = [m["input_per_1m"] for m in sorted_models]
    assert costs == sorted(costs)


def test_sort_by_context_largest_first():
    models = parse_models(SAMPLE_DATA)
    sorted_models = sort_models(models, "context")
    contexts = [m["context_tokens"] for m in sorted_models]
    assert contexts == sorted(contexts, reverse=True)


def test_sort_by_model_alphabetical():
    models = parse_models(SAMPLE_DATA)
    sorted_models = sort_models(models, "model")
    names = [m["model"] for m in sorted_models]
    assert names == sorted(names)


# --- add_estimated_cost ---


def test_add_estimated_cost():
    models = parse_models(SAMPLE_DATA)
    models = add_estimated_cost(models, input_tokens=1_000_000, output_tokens=100_000)
    claude = next(m for m in models if m["model"] == "claude-3-5-sonnet-20241022")
    # $3.00 * 1 + $15.00 * 0.1 = $4.50
    assert claude["est_cost"] == pytest.approx(4.50)


def test_add_estimated_cost_zero_tokens():
    models = parse_models(SAMPLE_DATA)
    models = add_estimated_cost(models, input_tokens=0, output_tokens=0)
    for m in models:
        assert m["est_cost"] == 0.0


# --- apply_price_changes ---


def test_apply_price_changes_new_model():
    models = parse_models(SAMPLE_DATA)
    cached = [m for m in models if m["model"] != "gpt-4o"]
    result = apply_price_changes(models, cached)
    gpt = next(m for m in result if m["model"] == "gpt-4o")
    assert gpt["input_change"] == "new"


def test_apply_price_changes_price_increase():
    models = parse_models(SAMPLE_DATA)
    cached = [dict(m) for m in models]
    # Simulate previous price was lower for claude
    claude_cached = next(m for m in cached if m["model"] == "claude-3-5-sonnet-20241022")
    claude_cached["input_per_1m"] = 2.0  # was $2, now $3
    result = apply_price_changes(models, cached)
    claude = next(m for m in result if m["model"] == "claude-3-5-sonnet-20241022")
    assert claude["input_change"] == "+$1.00"


def test_apply_price_changes_no_change():
    models = parse_models(SAMPLE_DATA)
    cached = [dict(m) for m in models]
    result = apply_price_changes(models, cached)
    for m in result:
        assert m.get("input_change") is None or m.get("input_change") == "new"


# --- print_table ---


def test_print_table_empty(capsys):
    print_table([])
    captured = capsys.readouterr()
    assert captured.err == "No models found.\n"


def test_print_table_outputs_headers(capsys):
    models = parse_models(SAMPLE_DATA)
    print_table(models)
    captured = capsys.readouterr()
    for header in ["Provider", "Model", "Input $/1M", "Output $/1M", "Context", "Vision", "Tools"]:
        assert header in captured.out


def test_print_table_outputs_model_count(capsys):
    models = parse_models(SAMPLE_DATA)
    print_table(models)
    captured = capsys.readouterr()
    assert "4 models" in captured.out


def test_print_table_shows_change_columns(capsys):
    models = parse_models(SAMPLE_DATA)
    cached = [dict(m) for m in models]
    next(m for m in cached if m["model"] == "gpt-4o")["input_per_1m"] = 1.0
    models = apply_price_changes(models, cached)
    print_table(models, show_changes=True)
    captured = capsys.readouterr()
    assert "Input Chg" in captured.out
    assert "Output Chg" in captured.out


def test_print_table_shows_est_cost_column(capsys):
    models = parse_models(SAMPLE_DATA)
    models = add_estimated_cost(models, 1_000_000, 100_000)
    print_table(models, show_est_cost=True)
    captured = capsys.readouterr()
    assert "Est. Cost" in captured.out
