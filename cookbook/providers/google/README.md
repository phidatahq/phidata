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
python cookbook/providers/google/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/google/basic.py
```

### 5. Run Agent with Tools

- Yahoo Finance with streaming on

```shell
python cookbook/providers/google/agent_stream.py
```

- Yahoo Finance without streaming

```shell
python cookbook/providers/google/agent.py
```

- Finance Agent

```shell
python cookbook/providers/google/finance_agent.py
```

- Web Search Agent

```shell
python cookbook/providers/google/web_search.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/providers/google/structured_output.py
```

