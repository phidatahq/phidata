# Ollama Hermes Cookbook

> Note: Fork and clone this repository if needed

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and run models

Run your chat model

```shell
ollama run hermes3
```

Message `/bye` to exit the chat model

### 2. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 3. Install libraries

```shell
pip install -U ollama duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/hermes/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/hermes/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/hermes/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/hermes/agent.py
```

- Finance Agent

```shell
python cookbook/providers/hermes/finance_agent.py
```

- Data Analyst

```shell
python cookbook/providers/hermes/data_analyst.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/hermes/structured_output.py
```

### 7. Run Agent that uses web search

```shell
python cookbook/providers/hermes/web_search.py
```
