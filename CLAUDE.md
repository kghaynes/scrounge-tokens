# CLAUDE.md

This file provides guidance to AI assistants working in this repository.

## Project Overview

**scrounge-tokens** is a Python script to pull current AI model information and associated token costs.

**Goal**: Retrieve up-to-date model names and pricing (input/output token costs) from AI providers and display them in a useful format.

## Repository Status

Core language has been chosen (Python). No source code exists yet — the first task is to implement the script.

## Implementation Approach

- **Language**: Python 3.10+
- **Target data**: Model names, input token costs, output token costs, context window sizes — per provider.
- **Providers to consider**: Anthropic, OpenAI, Google (Gemini), Mistral, etc.
- **Data source options**: Official provider pricing pages (web scraping), official APIs if available, or community-maintained data sources (e.g. `litellm` pricing data).

## Development Conventions

### General
- Keep the implementation simple and focused — a single script is the goal, not a framework.
- Prefer readable code over clever code.
- Avoid unnecessary dependencies; use the standard library where possible.

### Python
- Use Python 3.10+.
- Use `httpx` or `requests` for HTTP calls.
- Format with `black` and lint with `ruff`.
- Run tests with `pytest`.
- Use `pyproject.toml` for project configuration.

### Commands
```bash
# Install dependencies
pip install -e ".[dev]"

# Format
black .

# Lint
ruff check .

# Test
pytest
```

## Git Conventions

- **Main branch**: `main`
- **Feature branches**: `claude/<description>-<id>`
- Write clear, descriptive commit messages that explain *why* a change was made.
- Keep commits focused — one logical change per commit.

## File Structure

```
scrounge-tokens/
├── CLAUDE.md               # This file
├── README.md               # Project overview
├── pyproject.toml          # Project config, dependencies, tool settings
├── src/
│   └── scrounge_tokens/
│       ├── __init__.py
│       └── main.py         # Core script
├── tests/
│   └── test_main.py
└── .github/
    └── workflows/          # CI/CD (optional)
```

## Open Questions (clarify with user before implementing)

- Which providers to target first?
- Should output go to stdout, a file, or both?
- Should output be human-readable (table), JSON, or CSV?
