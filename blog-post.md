---
title: "I Built a Profiler for My LLM Bill (and It Saved Me $30/month)"
published: false
description: Track exactly which file, function, and feature is eating your OpenAI budget with a Python decorator.
tags: python, ai, llm, devtools, openai
cover_image: ""
---

Last month I got my OpenAI bill. **$47**. I had no idea which feature was eating it.

Was it the summarizer I hacked together at 2am? The classifier I thought was "lightweight"? I literally did not know. I just paid it.

That's when I built **llm-spend** — a Python profiler for your AI bill.

---

## The Problem: AI Costs Are Invisible Until the Bill Arrives

Every other resource in your stack is observable:
- CPU? `htop`.
- Memory? `psutil`.
- DB queries? Django Debug Toolbar, pg_stat_statements.

But LLM costs? You find out at the end of the month. Or when your API key gets rate-limited.

There's no `strace` for OpenAI. No flamegraph for Anthropic. Just a number on an invoice.

---

## The Solution: A Decorator That Tracks Costs Automatically

```python
from llm_spend import track

@track(model="gpt-4o", label="summarize")
def summarize_article(text: str):
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": text}],
    )
    return response  # llm-spend reads .usage automatically
```

That's it. Now every call through `summarize_article` is logged to a local SQLite database with:
- timestamp
- model used
- input/output tokens
- cost in USD
- source file and function name

Then run this from your terminal:

```bash
$ llm-spend report --by file
```

```
                   Cost by File
 File                  Calls  Input Tokens  Output Tokens  Cost (USD)
 src/summarizer.py        87       434,000         87,000    $2.9545
 src/classifier.py        12        24,000          3,600    $0.0960
 src/onboarding.py         3         6,000          1,500    $0.0300
```

Turns out: my "quick" article summarizer was eating 88% of my budget.

---

## The Pricing Table

Here are the real prices built into `llm-spend`:

| Model | Input $/1M | Output $/1M |
|-------|-----------|------------|
| claude-sonnet-4 | $3.00 | $15.00 |
| claude-opus-4 | $15.00 | $75.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| o1 | $15.00 | $60.00 |
| gemini-1.5-pro | $1.25 | $5.00 |
| gemini-2.0-flash | $0.10 | $0.40 |

Output tokens are almost always the expensive part. A model that costs 4x more on input might cost 10x more on output.

---

## How It Detects Costs Automatically

`llm-spend` doesn't require you to pass token counts manually. It inspects the response object from your LLM SDK:

**OpenAI:**
```python
response.usage.prompt_tokens      # → input_tokens
response.usage.completion_tokens  # → output_tokens
```

**Anthropic:**
```python
response.usage.input_tokens   # → input_tokens
response.usage.output_tokens  # → output_tokens
```

It figures out which format to use based on what attributes the object has. No configuration needed.

If you need manual control (for streaming or custom SDKs), use the context manager:

```python
from llm_spend import spending

with spending("claude-sonnet-4", label="classify") as s:
    response = client.messages.create(...)
    s.input_tokens = response.usage.input_tokens
    s.output_tokens = response.usage.output_tokens
```

---

## What I Learned Building This

**1. Output tokens are a trap.** The pricing tables make it obvious: output is always 3-5x more expensive per token than input. Summarization tasks that produce long outputs are disproportionately expensive.

**2. The response object is enough.** I don't need to intercept API calls or monkey-patch SDKs. Every major LLM SDK returns a response object with a `.usage` field. A simple `getattr()` chain is sufficient.

**3. SQLite is perfect for this.** Local, zero-config, and the schema is simple. No need for a remote database. This is a developer tool — it lives on the machine where the code runs.

**4. The `inspect.stack()` trick.** To know *which file and function* called the tracked function, I use `inspect.stack()[1]` inside the wrapper. This gives the caller's frame, not the wrapper's frame. Cheap and accurate.

---

## Install It

```bash
pip install llm-spend
```

Full docs and source: [github.com/LakshmiSravyaVedantham/llm-spend](https://github.com/LakshmiSravyaVedantham/llm-spend)

```bash
# Quick start
llm-spend summary       # total spend + top consumers
llm-spend report        # breakdown by model
llm-spend report --by file      # breakdown by source file
llm-spend export --format csv   # export to CSV
llm-spend models        # list all supported models and prices
```

If you're building anything with LLMs and don't track costs per feature, you're flying blind. `llm-spend` fixes that in 3 lines.

---

*Built in Python. No external AI SDK dependencies. Works with OpenAI, Anthropic, Google Gemini, and anything else that returns a response object with a `.usage` field.*
