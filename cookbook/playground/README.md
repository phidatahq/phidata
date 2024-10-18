# Agent UI

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your API keys

```shell
export OPENAI_API_KEY=***
export EXA_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai exa_py duckduckgo-search yfinance lancedb tantivy pypdf sqlalchemy 'fastapi[standard]' phidata youtube-transcript-api
```

### 4. Authenticate with phidata.app

```
phi auth
```

### 5. Run the Agent UI

```shell
python cookbook/playground/demo.py
```
