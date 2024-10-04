# Anyscale Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `ANYSCALE_API_KEY`

```shell
export ANYSCALE_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/anyscale/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/anyscale/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/anyscale/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/anyscale/agent.py
```

- Finance Agent

```shell
python cookbook/providers/anyscale/finance_agent.py
```

- Data Analyst

```shell
python cookbook/providers/anyscale/data_analyst.py
```

- DuckDuckGo Search
```shell
python cookbook/providers/together/web_search.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/anyscale/structured_output.py
```


