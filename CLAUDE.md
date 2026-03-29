# CLAUDE.md

This file provides guidance to AI assistants working in this repository.

## Project Overview

**scrounge-tokens** is a script to pull current AI model information and associated token costs. This is the owner's first attempt using Claude for coding assistance.

**Goal**: Build tooling that retrieves up-to-date model names and pricing (input/output token costs) from AI providers.

## Repository Status

This project is in its initial stages — no source code exists yet. The repository contains only this documentation and a README. The first task will be to implement the core script.

## Suggested Implementation Approach

When implementing the script, consider:

- **Language**: No language has been chosen yet. Python is a natural fit for scripting tasks like this (good HTTP library support, easy JSON parsing, wide familiarity).
- **Target data**: Model names, input token costs, output token costs, context window sizes — per provider.
- **Providers to consider**: Anthropic, OpenAI, Google (Gemini), Mistral, etc.
- **Data source options**: Official provider pricing pages (web scraping), official APIs if available, or community-maintained data sources.

## Development Conventions

Since no conventions are established yet, follow these defaults:

### General
- Keep the implementation simple and focused — a single script is the goal, not a framework.
- Prefer readable code over clever code.
- Avoid unnecessary dependencies; use the standard library where possible.

### If Python is chosen
- Use Python 3.10+.
- Use `requests` or `httpx` for HTTP calls if needed.
- Format with `black` and lint with `ruff` or `flake8`.
- Run tests with `pytest`.
- Use `pyproject.toml` for project configuration.

### If Node.js/TypeScript is chosen
- Use Node 18+ with TypeScript.
- Format with `prettier`, lint with `eslint`.
- Run tests with `jest` or `vitest`.
- Use `package.json` for project configuration.

## Git Conventions

- **Main branch**: `main`
- **Feature branches**: `claude/<description>-<id>` (as seen in the current branch naming)
- Write clear, descriptive commit messages that explain *why* a change was made.
- Keep commits focused — one logical change per commit.

## File Structure (Anticipated)

Once implemented, the structure will likely look like:

```
scrounge-tokens/
├── CLAUDE.md           # This file
├── README.md           # Project overview
├── src/                # Source code (or script at root level)
│   └── main.py         # Core script
├── tests/              # Test files
│   └── test_main.py
├── pyproject.toml      # Project config (if Python)
└── .github/
    └── workflows/      # CI/CD (optional)
```

## Working in This Repo

- **No build step exists yet** — add one when the language/toolchain is decided.
- **No tests exist yet** — add them alongside the first implementation.
- **No CI/CD exists yet** — consider adding a GitHub Actions workflow once there is something to test.
- Before implementing, clarify with the user: preferred language, which providers to target, and whether output should go to stdout, a file, or both.
