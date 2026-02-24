# llm-spend

**Track your AI API costs per file, function, and feature. Because "$47 last month" is not a cost report.**

[![CI](https://github.com/LakshmiSravyaVedantham/llm-spend/actions/workflows/ci.yml/badge.svg)](https://github.com/LakshmiSravyaVedantham/llm-spend/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/llm-spend)](https://pypi.org/project/llm-spend/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Quick Install

```bash
pip install llm-spend
```

## 3-Line Usage

```python
from llm_spend import track

@track(model="gpt-4o", label="summarize")
def summarize(text):
    return openai_client.chat.completions.create(...)
```

Then from your terminal:

```
$ llm-spend summary
```

```
╭─ LLM Spend Summary (last 30 days) ────────────────────────────╮
│ Total Spend:   $3.2741                                         │
│ Total Calls:   142                                             │
│ Input Tokens:  1,234,000                                       │
│ Output Tokens: 98,000                                          │
│                                                                │
│ Top File:      src/summarizer.py                               │
│ Top Model:     gpt-4o                                          │
╰────────────────────────────────────────────────────────────────╯
```

---

## Why llm-spend?

LLM costs are invisible until the bill arrives. You know you spent $47 last month — but *which feature* ate it?

`llm-spend` works like a profiler, but for your AI bill. Wrap any function that calls an LLM and get a breakdown by file, function, label, or model.

---

## Usage

### Decorator

```python
from llm_spend import track

@track(model="gpt-4o", label="classify")
def classify_intent(text: str):
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": text}],
    )
    return response   # llm-spend reads usage automatically
```

### Context Manager (manual token counts)

```python
from llm_spend import spending

with spending("claude-sonnet-4", label="summarize") as s:
    response = anthropic_client.messages.create(...)
    s.input_tokens = response.usage.input_tokens
    s.output_tokens = response.usage.output_tokens
```

---

## CLI Commands

### Show report

```bash
llm-spend report                    # breakdown by model (default)
llm-spend report --by file          # breakdown by source file
llm-spend report --by function      # breakdown by function
llm-spend report --by label         # breakdown by label
llm-spend report --days 7           # last 7 days only
```

Example output (`--by file`):

```
             Cost by File
 File                  Calls  Input Tokens  Output Tokens  Cost (USD)
 src/summarizer.py        10        50,000         10,000     $0.2750
 src/classifier.py         5        20,000          5,000     $0.1000
```

### Summary

```bash
llm-spend summary
llm-spend summary --days 7
```

### Export logs

```bash
llm-spend export                          # CSV to llm_spend_TIMESTAMP.csv
llm-spend export --format json -o out.json
```

### Clear logs

```bash
llm-spend clear --days 7     # delete records older than 7 days
llm-spend clear              # delete all records (prompts for confirmation)
```

### List supported models and pricing

```bash
llm-spend models
```

---

## Supported Providers & Models

| Provider  | Models |
|-----------|--------|
| Anthropic | claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022, claude-opus-4, claude-sonnet-4 |
| OpenAI    | gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o1-mini |
| Google    | gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash |

Pricing is per 1M tokens and can be extended by editing `pricing.py`.

---

## How it works

1. Your function (or context manager block) calls the LLM.
2. `llm-spend` inspects the response object for `usage.prompt_tokens` / `usage.completion_tokens` (OpenAI) or `usage.input_tokens` / `usage.output_tokens` (Anthropic) automatically.
3. Cost is calculated from the built-in pricing table and stored in `~/.llm-spend/spend.db` (SQLite).
4. Run `llm-spend report` any time to see where your money is going.

No external SDK dependencies — works with any provider's response object.

---

## Development

```bash
git clone https://github.com/LakshmiSravyaVedantham/llm-spend
cd llm-spend
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

---

## License

MIT (c) 2026 sravyalu
