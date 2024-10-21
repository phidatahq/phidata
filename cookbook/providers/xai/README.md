# xAI Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `XAI_API_KEY`

```shell
export XAI_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai duckduckgo-search duckdb yfinance phidata
```

### 4. Run Finance Agent

```shell
python cookbook/providers/xai/finance_agent.py
```

### 5. Run Data Analyst Agent

```shell
python cookbook/providers/xai/data_analyst.py
```

### 6. Run Agent that uses web search

```shell
python cookbook/providers/xai/web_search.py
```
