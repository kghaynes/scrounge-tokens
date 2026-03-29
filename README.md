# scrounge-tokens

Fetches current AI model pricing (input/output token costs and context window sizes) from major providers and prints a formatted table to stdout.

**Providers**: Anthropic, OpenAI, Google (Gemini), NVIDIA

## Requirements

- Python 3.10+
- [httpx](https://www.python-httpx.org/) (installed automatically)

## Install

### First time (clone from GitHub)

```bash
git clone https://github.com/kghaynes/scrounge-tokens.git
cd scrounge-tokens
pip install -e .
```

### Get updates later

```bash
git pull origin main
```

## Usage

```bash
scrounge-tokens             # show all models
scrounge-tokens --help      # full options list
```

### Options

| Flag | Description |
|---|---|
| `--provider NAME` | Filter by provider: `anthropic`, `openai`, `google`, `nvidia` |
| `--min-context SIZE` | Minimum context window, e.g. `128k`, `1m` |
| `--max-cost DOLLARS` | Max input cost per 1M tokens |
| `--sort-by FIELD` | `provider` (default), `input-cost`, `output-cost`, `context`, `model` |
| `--input-tokens COUNT` | Estimate cost for this many input tokens, e.g. `1m`, `500k` |
| `--output-tokens COUNT` | Estimate cost for this many output tokens |
| `--json` | Output as JSON |
| `--csv` | Output as CSV |
| `--cached` | Use cached data instead of fetching (offline mode) |

### Examples

```bash
# Cheapest models first
scrounge-tokens --sort-by input-cost

# Only models with 128K+ context
scrounge-tokens --min-context 128k

# Anthropic models under $5/1M input tokens
scrounge-tokens --provider anthropic --max-cost 5

# Estimate cost of a 1M-token input + 100K-token output run
scrounge-tokens --input-tokens 1m --output-tokens 100k --sort-by input-cost

# Machine-readable output
scrounge-tokens --json
scrounge-tokens --csv
```

### Example output

```
Provider  | Model                       | Input $/1M | Output $/1M | Context | Vision | Tools
----------+-----------------------------+------------+-------------+---------+--------+------
Anthropic | claude-3-5-sonnet-20241022  | $3.00      | $15.00      | 200K    | Y      | Y
Anthropic | claude-opus-4-5             | $15.00     | $75.00      | 200K    | Y      | Y
Google    | gemini-1.5-pro              | $1.25      | $5.00       | 2M      | Y      | Y
NVIDIA    | meta/llama-3.1-8b-instruct  | $0.1000    | $0.1000     | 128K    | N      | N
OpenAI    | gpt-4o                      | $2.50      | $10.00      | 128K    | Y      | Y
...

42 models
```

On subsequent runs, any price changes since the last fetch are shown in `Input Chg` / `Output Chg` columns.

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
