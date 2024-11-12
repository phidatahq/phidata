# AWS Bedrock Anthropic Claude

[Models overview](https://docs.anthropic.com/claude/docs/models-overview)

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your AWS Credentials

```shell
export AWS_ACCESS_KEY_ID=***
export AWS_SECRET_ACCESS_KEY=***
export AWS_DEFAULT_REGION=***
```

### 3. Install libraries

```shell
pip install -U boto3 duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/bedrock/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/bedrock/basic.py
```

### 5. Run Agent with Tools

- YFinance Agent with streaming on

```shell
python cookbook/providers/bedrock/agent_stream.py
```

- YFinance Agent without streaming

```shell
python cookbook/providers/bedrock/agent.py
```

- Data Analyst

```shell
python cookbook/providers/bedrock/data_analyst.py
```

- Web Search

```shell
python cookbook/providers/bedrock/web_search.py
```

- Finance Agent

```shell
python cookbook/providers/bedrock/finance.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/bedrock/structured_output.py
```

### 7. Run Agent that uses storage

```shell
python cookbook/providers/bedrock/storage.py
```

### 8. Run Agent that uses knowledge

```shell
python cookbook/providers/bedrock/knowledge.py
```
