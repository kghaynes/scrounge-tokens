# scrounge-tokens

Fetches current AI model pricing (input/output token costs and context window sizes) from major providers and prints a formatted table to stdout.

**Providers**: Anthropic, OpenAI, Google (Gemini), NVIDIA

## Requirements

- Python 3.10+
- [httpx](https://www.python-httpx.org/) (installed automatically)

## Install

```bash
pip install -e .
```

## Usage

```bash
scrounge-tokens
```

Or run directly:

```bash
python -m scrounge_tokens.main
```

### Example output

```
Provider  | Model                       | Input $/1M | Output $/1M | Context
----------+-----------------------------+------------+-------------+---------
Anthropic | claude-3-5-sonnet-20241022  | $3.00      | $15.00      | 200K
Anthropic | claude-opus-4-5             | $15.00     | $75.00      | 200K
Google    | gemini-1.5-pro              | $1.25      | $5.00       | 2M
NVIDIA    | meta/llama-3.1-8b-instruct  | $0.1000    | $0.1000     | 128K
OpenAI    | gpt-4o                      | $2.50      | $10.00      | 128K
...

42 models
```

Pricing data is sourced from the [litellm community pricing database](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json).

## Development

```bash
pip install -e ".[dev]"

# Format
black .

# Lint
ruff check .

# Test
python3 -m pytest
```
