# Google Gemini Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export `GOOGLE_API_KEY`

```shell
export GOOGLE_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U google-generativeai duckduckgo-search yfinance phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/models/google/basic_stream.py
```

- Streaming off

```shell
python cookbook/models/google/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/models/google/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/models/google/agent.py
```

- Finance Agent

```shell
python cookbook/models/google/finance_agent.py
```

- Web Search Agent

```shell
python cookbook/models/google/web_search.py
```

- Data Analysis Agent

```shell
python cookbook/models/google/data_analyst.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/models/google/structured_output.py
```

### 7. Run Agent that uses storage

```shell
python cookbook/models/google/storage.py
```

### 8. Run Agent that uses knowledge

```shell
python cookbook/models/google/knowledge.py
```

### 9. Run Agent that interprets an audio file

```shell
python cookbook/models/google/audio_agent.py
```
