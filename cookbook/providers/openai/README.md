# OpenAI Chat function calling

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your OpenaiChat API Key

```shell
export OPENAI_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai duckduckgo-search duckdb yfinance exa_py phidata
```

### 4. Run Agent

- stream off

```shell
python cookbook/providers/openai/basic.py
```

- stream on

```shell
python cookbook/providers/openai/basic_stream.py
```

### 5. Run Agent with Tools

- DuckDuckGo Search

```shell
python cookbook/providers/openai/agent.py
```

- DuckDuckGo Search Stream

```shell
python cookbook/providers/openai/agent_stream.py
```

- YFinance

```shell
python cookbook/providers/openai/finance.py
```

- Exa Search

```shell
python cookbook/providers/openai/exa_search.py
```

- Data Analyst

```shell
python cookbook/providers/openai/data_analyst.py
```

### 6. Run Agent with Structured output

```shell
python cookbook/providers/openai/structured_output.py
```


