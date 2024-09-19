# Anthropic Claude

[Models overview](https://docs.anthropic.com/claude/docs/models-overview)

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Set your `ANTHROPIC_API_KEY`

```shell
export ANTHROPIC_API_KEY=xxx
```

### 3. Install libraries

```shell
pip install -U anthropic duckduckgo-search duckdb yfinance exa_py phidata
```

### 4. Run Agent

- stream on

```shell
python cookbook/providers/claude/assistant.py
```

- stream off

```shell
python cookbook/providers/claude/assistant_stream_off.py
```

### 5. Run Agent with Tools

- YFinance

```shell
python cookbook/providers/claude/finance.py
```

- Data Analyst

```shell
python cookbook/providers/claude/data_analyst.py
```

- Exa Search

```shell
python cookbook/providers/claude/exa_search.py
```

### 6. Run Agent with Structured output

```shell
python cookbook/providers/claude/structured_output.py
```
