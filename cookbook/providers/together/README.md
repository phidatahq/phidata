# Together Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `TOGETHER_API_KEY`

```shell
export TOGETHER_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U together openai duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/together/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/together/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/together/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/together/agent.py
```

- Finance Agent

```shell
python cookbook/providers/together/finance_agent.py
```

- Data Analyst

```shell
python cookbook/providers/together/data_analyst.py
```

- DuckDuckGo Search
```shell
python cookbook/providers/together/web_search.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/together/structured_output.py
```

