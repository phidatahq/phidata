# Azure OpenAI Chat function calling

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Save the following environment variables in a .env file (see .env-template). Python-dotenv will load them into memory on run time.

```shell
AZURE_OPENAI_MODEL_NAME="gpt-4o"
AZURE_OPENAI_API_KEY=""
AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT="gpt-4o"
```

### 3. Install libraries

```shell
pip install -U python-dotenv openai duckduckgo-search duckdb yfinance exa_py phidata
```

### 4. Run Agent

- stream off

```shell
python cookbook/providers/azure_openai/basic.py
```

- stream on

```shell
python cookbook/providers/azure_openai/basic_stream.py
```

### 5. Run Agent with Tools

- DuckDuckGo Search

```shell
python cookbook/providers/azure_openai/agent.py
```

- DuckDuckGo Search Stream

```shell
python cookbook/providers/azure_openai/agent_stream.py
```

- YFinance

```shell
python cookbook/providers/azure_openai/finance.py
```

- Exa Search

```shell
python cookbook/providers/azure_openai/exa_search.py
```

- Data Analyst

```shell
python cookbook/providers/azure_openai/data_analyst.py
```

### 6. Run Agent with Structured output

```shell
python cookbook/providers/azure_openai/structured_output.py
```


