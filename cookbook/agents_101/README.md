# Agents 101

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai duckduckgo-search duckdb yfinance lancedb tantivy pypdf sqlalchemy 'fastapi[standard]' phidata
```

### 4. Run the Web Search Agent

```shell
python cookbook/agents_101/01_web_search.py
```

### 5. Run the Finance Agent

```shell
python cookbook/agents_101/02_finance_agent.py
```

### 6. Run the RAG Agent

```shell
python cookbook/agents_101/03_rag_agent.py
```

### 7. Test in Agent UI

Authenticate with phidata.app

```
phi auth
```

Run the Agent UI

```shell
python cookbook/agents_101/04_agent_ui.py
```
