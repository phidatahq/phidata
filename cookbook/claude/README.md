# Claude function calling

[Models overview](https://docs.anthropic.com/claude/docs/models-overview)

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your Anthropic API Key

```shell
export ANTHROPIC_API_KEY=xxx
```

### 3. Install libraries

```shell
pip install -U anthropic phidata duckduckgo-search duckdb yfinance exa_py
```

### 4. Web search function calling

```shell
python cookbook/claude/web_search.py
```

### 5. YFinance function calling

```shell
python cookbook/claude/finance.py
```

### 6. Structured output

```shell
python cookbook/claude/structured_output.py
```

### 7. Data Analyst

```shell
python cookbook/claude/data_analyst.py
```

### 8. Exa Search

```shell
python cookbook/claude/exa_search.py
```
