# CLAUDE.md

This file provides guidance to AI assistants working in this repository.

## Project Overview

**scrounge-tokens** is a Python script that fetches current AI model pricing (input/output token costs and context window sizes) from major providers and prints a formatted table to stdout.

**Providers**: Anthropic, OpenAI, Google (Gemini), NVIDIA
**Data source**: [litellm pricing database](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) — a community-maintained JSON file on GitHub
**Output**: ASCII table to stdout (human-readable and AI-parseable)

## Repository Structure

```
scrounge-tokens/
├── CLAUDE.md
├── README.md
├── pyproject.toml                   # Project config, dependencies, tool settings
├── src/
│   └── scrounge_tokens/
│       ├── __init__.py
│       └── main.py                  # Core script
└── tests/
    ├── __init__.py
    └── test_main.py
```

## Development Setup

```bash
pip install -e ".[dev]"
```

## Commands

```bash
# Run the script
scrounge-tokens
# or
python -m scrounge_tokens.main

# Format
black .

# Lint
ruff check .

# Test
python3 -m pytest
```

## Architecture

All logic lives in `src/scrounge_tokens/main.py`:

| Function | Purpose |
|---|---|
| `fetch_pricing()` | Fetches the litellm pricing JSON via HTTP |
| `parse_models(data)` | Filters to target providers, extracts cost/context fields |
| `print_table(models)` | Renders the ASCII table to stdout |
| `_strip_prefix(key)` | Removes litellm provider prefixes (e.g. `gemini/`) from model names |
| `_format_context(tokens)` | Formats token counts as `128K`, `1M`, etc. |
| `_format_cost(cost)` | Formats per-1M-token cost as a dollar amount |
| `main()` | Entry point — fetch, parse, print |

### Provider Mapping

litellm uses these provider keys, mapped to display names:

| litellm key | Display name |
|---|---|
| `anthropic` | Anthropic |
| `openai` | OpenAI |
| `google` | Google |
| `nvidia_nim` | NVIDIA |

Models with `mode: embedding`, `mode: image_generation`, etc. are excluded — only chat/completion models are shown.

## Development Conventions

- Python 3.10+
- `httpx` for HTTP
- `black` for formatting, `ruff` for linting
- `pytest` for tests
- Keep logic in `main.py` — no need for multiple modules unless complexity grows significantly

## Git Conventions

- **Main branch**: `main`
- **Feature branches**: `claude/<description>-<id>`
- Clear, descriptive commit messages explaining *why* a change was made
- One logical change per commit
