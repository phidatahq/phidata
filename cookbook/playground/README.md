# Agent UI

> Note: Fork and clone this repository if needed

### Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

## OpenAI Agents

### Export your API keys

```shell
export OPENAI_API_KEY=***
export EXA_API_KEY=***
```

### Install libraries

```shell
pip install -U openai exa_py duckduckgo-search yfinance pypdf sqlalchemy 'fastapi[standard]' phidata youtube-transcript-api
```

### Authenticate with phidata.app

```
phi auth
```

### Connect OpenAI Agents to the Agent UI

```shell
python cookbook/playground/demo.py
```

## Fully local Ollama Agents

### Pull llama3.1:8b

```shell
ollama pull llama3.1:8b
```

### Install libraries

```shell
pip install -U ollama duckduckgo-search yfinance pypdf sqlalchemy 'fastapi[standard]' phidata youtube-transcript-api
```

### Authenticate with phidata.app

```
phi auth
```

### Connect Ollama agents to the Agent UI

```shell
python cookbook/playground/ollama_agents.py
```
