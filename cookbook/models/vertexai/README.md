# VertexAI Gemini Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Authenticate with Google Cloud

[Authenticate with Gcloud](https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstarts/quickstart-multimodal)

### 3. Install libraries

```shell
pip install -U google-cloud-aiplatform duckduckgo-search yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/vertexai/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/vertexai/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/vertexai/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/vertexai/agent.py
```

- Finance Agent

```shell
python cookbook/providers/vertexai/finance_agent.py
```

- Web Search Agent

```shell
python cookbook/providers/vertexai/web_search.py
```

- Data Analysis Agent

```shell
python cookbook/providers/vertexai/data_analyst.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/vertexai/structured_output.py
```

### 7. Run Agent that uses storage

```shell
python cookbook/providers/vertexai/storage.py
```

### 8. Run Agent that uses knowledge

```shell
python cookbook/providers/vertexai/knowledge.py
```
