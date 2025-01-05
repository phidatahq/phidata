# Openrouter Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `OPENROUTER_API_KEY`

```shell
export OPENROUTER_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/openrouter/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/openrouter/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/openrouter/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/openrouter/agent.py
```

- Web Search Agent

```shell
python cookbook/providers/openrouter/web_search.py
```

- Data Analyst

```shell
python cookbook/providers/openrouter/data_analyst.py
```

- Finance Agent

```shell
python cookbook/providers/openrouter/finance_agent.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/openrouter/structured_output.py
```


