# Groq Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `GROQ_API_KEY`

```shell
export GROQ_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U groq duckduckgo-search duckdb yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/models/groq/basic_stream.py
```

- Streaming off

```shell
python cookbook/models/groq/basic.py
```

### 5. Run Agent with Tools

- DuckDuckGo Search with streaming on

```shell
python cookbook/models/groq/agent_stream.py
```

- DuckDuckGo Search without streaming

```shell
python cookbook/models/groq/agent.py
```

- Finance Agent

```shell
python cookbook/models/groq/finance_agent.py
```

- Data Analyst

```shell
python cookbook/models/groq/data_analyst.py
```

- Web Search

```shell
python cookbook/models/groq/web_search.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/models/groq/structured_output.py
```

### 7. Run Agent that uses storage

Please run pgvector in a docker container using:

```shell
./cookbook/run_pgvector.sh
```

Then run the following:

```shell
python cookbook/models/groq/storage.py
```

### 8. Run Agent that uses knowledge

```shell
python cookbook/models/groq/knowledge.py
```
Take note that by default, OpenAI embeddings are used and an API key will be required. Alternatively, there are other embedders available that can be used. See more examples in `/cookbook/knowledge/embedders`


### 9. Run Playground with some Agents

```shell
python cookbook/models/groq/knowledge.py
```

### 10. Run in async mode

```shell
python cookbook/models/groq/async/basic_stream.py
```
```shell
python cookbook/models/groq/async/basic.py
```
```shell
python cookbook/models/groq/async/data_analyst.py
```
```shell
python cookbook/models/groq/async/finance_agent.py
```
```shell
python cookbook/models/groq/async/hackernews.py
```