# Azure OpenAI Chat Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export environment variables

```shell
export AZURE_OPENAI_MODEL_NAME="gpt-4o"
export AZURE_OPENAI_API_KEY=***
export AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT=***
export AZURE_OPENAI_API_VERSION="2024-02-01"
export AWS_DEFAULT_REGION=us-east-1
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

- Web Search

```shell
python cookbook/providers/azure_openai/web_search.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/azure_openai/structured_output.py
```

### 7. Run Agent that uses storage

```shell
python cookbook/providers/azure_openai/storage.py
```

### 8. Run Agent that uses knowledge

```shell
python cookbook/providers/azure_openai/knowledge.py
```
