# Mistral Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `MISTRAL_API_KEY`

```shell
export MISTRAL_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U mistralai duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/models/mistral/basic_stream.py
```

- Streaming off

```shell
python cookbook/models/mistral/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/models/mistral/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/models/mistral/agent.py
```

- Finance Agent

```shell
python cookbook/models/mistral/finance_agent.py
```

- Data Analyst

```shell
python cookbook/models/mistral/data_analyst.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/models/mistral/structured_output.py
```

### 7. Run Agent that uses web search

```shell
python cookbook/models/mistral/web_search.py
```