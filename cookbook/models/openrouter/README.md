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
python cookbook/models/openrouter/basic_stream.py
```

- Streaming off

```shell
python cookbook/models/openrouter/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/models/openrouter/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/models/openrouter/agent.py
```

- Web Search Agent

```shell
python cookbook/models/openrouter/web_search.py
```

- Data Analyst

```shell
python cookbook/models/openrouter/data_analyst.py
```

- Finance Agent

```shell
python cookbook/models/openrouter/finance_agent.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/models/openrouter/structured_output.py
```


