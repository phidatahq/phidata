# OpenAI Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/openai/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/openai/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/openai/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/openai/agent.py
```

- Finance Agent

```shell
python cookbook/providers/openai/finance_agent.py
```

- Data Analyst

```shell
python cookbook/providers/openai/data_analyst.py
```

- Web Search

```shell
python cookbook/providers/openai/web_search.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/openai/structured_output.py
```

### 7. Run Agent uses memory

```shell
python cookbook/providers/openai/memory.py
```

### 8. Run Agent that uses storage

```shell
python cookbook/providers/openai/storage.py
```

### 9. Run Agent that uses knowledge

```shell
python cookbook/providers/openai/knowledge.py
```
