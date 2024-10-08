# Ollama Cookbook

> Note: Fork and clone this repository if needed
> Ollama Model class has been designed to work with llama models. Support for more model classes coming soon

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and run models

Run your chat model

```shell
ollama run llama3.2
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
python cookbook/providers/ollama/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/ollama/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/ollama/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/ollama/agent.py
```

- Finance Agent

```shell
python cookbook/providers/ollama/finance_agent.py
```

- Data Analyst

```shell
python cookbook/providers/ollama/data_analyst.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/ollama/structured_output.py
```

### 7. Run Agent that uses web search

```shell
python cookbook/providers/ollama/web_search.py
```
