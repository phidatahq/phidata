# xAI Agents

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

### 5. Run Data Analyst

```shell
python cookbook/providers/xai/data_analyst.py
```

### 6. Run Web Search Agent

```shell
python cookbook/providers/xai/web_search.py
```

### 7. Summarize youtube videos using xAI
