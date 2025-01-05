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

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/xai/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/xai/basic.py
```

### 5. Run with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/xai/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/xai/agent.py
```

- Finance Agent

```shell
python cookbook/providers/xai/finance_agent.py
```

- Data Analyst

```shell
python cookbook/providers/xai/data_analyst.py
```

- Web Search

```shell
python cookbook/providers/xai/web_search.py
```
