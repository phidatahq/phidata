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
python cookbook/models/claude/basic_stream.py
```

- Streaming off

```shell
python cookbook/models/claude/basic.py
```

### 5. Run Agent with Tools

- YFinance Agent with streaming on

```shell
python cookbook/models/claude/agent_stream.py
```

- YFinance Agent without streaming

```shell
python cookbook/models/claude/agent.py
```

- Data Analyst

```shell
python cookbook/models/claude/data_analyst.py
```

- Web Search

```shell
python cookbook/models/claude/web_search.py
```

- Finance Agent

```shell
python cookbook/models/claude/finance.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/models/claude/structured_output.py
```

### 7. Run Agent that uses storage

```shell
python cookbook/models/claude/storage.py
```

### 8. Run Agent that uses knowledge

Take note that claude uses OpenAI embeddings under the hood, and you will need an OpenAI API Key
```shell
export OPENAI_API_KEY=***
```

```shell
python cookbook/models/claude/knowledge.py
```


