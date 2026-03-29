"""Tests for scrounge_tokens.main."""

import pytest

from scrounge_tokens.main import (
    _format_context,
    _format_cost,
    _strip_prefix,
    parse_models,
    print_table,
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


# --- parse_models ---

SAMPLE_DATA = {
    "claude-3-5-sonnet-20241022": {
        "litellm_provider": "anthropic",
        "mode": "chat",
        "input_cost_per_token": 0.000003,
        "output_cost_per_token": 0.000015,
        "max_input_tokens": 200_000,
    },
    "gpt-4o": {
        "litellm_provider": "openai",
        "mode": "chat",
        "input_cost_per_token": 0.0000025,
        "output_cost_per_token": 0.00001,
        "max_input_tokens": 128_000,
    },
    "gemini/gemini-1.5-pro": {
        "litellm_provider": "google",
        "mode": "chat",
        "input_cost_per_token": 0.00000125,
        "output_cost_per_token": 0.000005,
        "max_input_tokens": 2_000_000,
    },
    "nvidia_nim/meta/llama-3.1-8b-instruct": {
        "litellm_provider": "nvidia_nim",
        "mode": "chat",
        "input_cost_per_token": 0.0000001,
        "output_cost_per_token": 0.0000001,
        "max_input_tokens": 128_000,
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


def test_parse_models_count():
    models = parse_models(SAMPLE_DATA)
    assert len(models) == 4


def test_parse_models_excludes_embeddings():
    models = parse_models(SAMPLE_DATA)
    model_names = [m["model"] for m in models]
    assert "text-embedding-3-small" not in model_names


def test_parse_models_excludes_unknown_provider():
    models = parse_models(SAMPLE_DATA)
    providers = {m["provider"] for m in models}
    assert "unknown_provider" not in providers


def test_parse_models_excludes_no_pricing():
    models = parse_models(SAMPLE_DATA)
    model_names = [m["model"] for m in models]
    assert "free-model" not in model_names


def test_parse_models_strips_gemini_prefix():
    models = parse_models(SAMPLE_DATA)
    model_names = [m["model"] for m in models]
    assert "gemini-1.5-pro" in model_names


def test_parse_models_strips_nvidia_prefix():
    models = parse_models(SAMPLE_DATA)
    model_names = [m["model"] for m in models]
    assert "meta/llama-3.1-8b-instruct" in model_names


def test_parse_models_cost_conversion():
    models = parse_models(SAMPLE_DATA)
    claude = next(m for m in models if m["model"] == "claude-3-5-sonnet-20241022")
    assert claude["input_per_1m"] == pytest.approx(3.0)
    assert claude["output_per_1m"] == pytest.approx(15.0)


def test_parse_models_sorted():
    models = parse_models(SAMPLE_DATA)
    providers = [m["provider"] for m in models]
    assert providers == sorted(providers)


# --- print_table ---


def test_print_table_empty(capsys):
    print_table([])
    captured = capsys.readouterr()
    assert captured.err == "No models found.\n"


def test_print_table_outputs_headers(capsys):
    models = parse_models(SAMPLE_DATA)
    print_table(models)
    captured = capsys.readouterr()
    assert "Provider" in captured.out
    assert "Model" in captured.out
    assert "Input $/1M" in captured.out
    assert "Output $/1M" in captured.out
    assert "Context" in captured.out


def test_print_table_outputs_model_count(capsys):
    models = parse_models(SAMPLE_DATA)
    print_table(models)
    captured = capsys.readouterr()
    assert "4 models" in captured.out
