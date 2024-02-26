# Mistral AI

> Note: Fork and clone this repository if needed

## Build AI Assistants with Mistral

1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U mistralai phidata
```

3. Export your Mistral API Key

```shell
export MISTRAL_API_KEY=xxx
```

4. Run Assistant

```shell
python cookbook/mistral/assistant.py
```

5. Run Assistant with Tool calls

```shell
pip install duckduckgo-search

python cookbook/mistral/tool_call.py
```

## Build RAG AI App with Mistral & PgVector

1. Start pgvector

```shell
phi start cookbook/mistral/resources.py -y
```

2. Install libraries

```shell
pip install -U pgvector pypdf psycopg sqlalchemy google-cloud-aiplatform phidata
```

3. Run RAG App

```shell
python cookbook/mistral/app.py
```

4. Stop pgvector

```shell
phi stop cookbook/mistral/resources.py -y
```
