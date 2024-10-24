# Anthropic Claude

[Models overview](https://docs.anthropic.com/claude/docs/models-overview)

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Set your `ANTHROPIC_API_KEY`

```shell
export ANTHROPIC_API_KEY=xxx
```

### 3. Install libraries

```shell
pip install -U anthropic duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/claude/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/claude/basic.py
```

### 5. Run Agent with Tools

- YFinance Agent with streaming on

```shell
python cookbook/providers/claude/agent_stream.py
```

- YFinance Agent without streaming

```shell
python cookbook/providers/claude/agent.py
```

- Data Analyst

```shell
python cookbook/providers/claude/data_analyst.py
```

- Web Search

```shell
python cookbook/providers/claude/web_search.py
```

- Finance Agent

```shell
python cookbook/providers/claude/finance.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/claude/structured_output.py
```

### 7. Run Agent that uses memory

```shell
python cookbook/providers/claude/memory.py
```

### 8. Run Agent that uses storage

```shell
python cookbook/providers/claude/storage.py
```

### 9. Run Agent that uses knowledge

```shell
python cookbook/providers/claude/knowledge.py
```
