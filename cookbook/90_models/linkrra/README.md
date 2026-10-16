# Linkrra Cookbook

This cookbook demonstrates how to use Linkrra with the Agno framework. Linkrra's Synap API serves
open-weight models such as Qwen3 Coder, gpt-oss and Gemma 4 behind an OpenAI-compatible Chat
Completions endpoint.

> **Prerequisites**: Fork and clone this repository if needed

## Quick Start

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `LINKRRA_API_KEY`

Get your API key from: https://synap.linkrra.com/account

```shell
export LINKRRA_API_KEY=***
```

### 3. Install libraries

```shell
uv pip install -U openai agno
```

### 4. Run basic Agent

```shell
python cookbook/90_models/linkrra/basic.py
```

### 5. Run Agent with Tools

```shell
python cookbook/90_models/linkrra/tool_use.py
```

## Model Ids

- `qwen3-coder-30b` (default) — 32,768 context
- `gpt-oss-20b` — 32,768 context
- `gemma-4-26b-a4b-it` — 131,072 context

Tool calling and JSON-schema structured output work on all three models. `tool_choice="required"`
is supported on `qwen3-coder-30b` and `gpt-oss-20b`.

The three models above run on Linkrra's own hardware. Their context lengths, prices and supported
parameters are published at `GET /v1/models?format=openrouter`; read the current list from there
rather than hardcoding it. The plain `GET /v1/models` endpoint also lists models that Linkrra routes
to other hosts.

## Resources & Support

### 🔗 Official Links
- [Website](https://synap.linkrra.com)
- [Documentation](https://synap.linkrra.com/docs)
- [Pricing](https://synap.linkrra.com/pricing)
- [Get API Key](https://synap.linkrra.com/account)

### 📖 API Reference
- **Base URL**: `https://pool.linkrra.com/v1`
- **Models Endpoint**: `https://pool.linkrra.com/v1/models?format=openrouter`
