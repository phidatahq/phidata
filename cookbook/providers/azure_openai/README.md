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
pip install -U openai duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/azure_openai/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/azure_openai/basic.py
```

### 5. Run Agent with Tools

- DuckDuckGo Search with streaming on

```shell
python cookbook/providers/azure_openai/agent_stream.py
```

- DuckDuckGo Search without streaming

```shell
python cookbook/providers/azure_openai/agent.py
```

- Finance Agent

```shell
python cookbook/providers/azure_openai/finance_agent.py
```

- Data Analyst

```shell
python cookbook/providers/azure_openai/data_analyst.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/azure_openai/structured_output.py
```

### 7. Run Agent that uses web search

```shell
python cookbook/providers/azure_openai/web_search.py
```
