# Assistants Cookbook

Phidata Assistants add memory, knowledge and tools to LLMs. Let's test out a few examples.

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U phidata openai
```

3. Run PgVector (If using Assistant with Knowledge and/or Memory)

- Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) for running PgVector in a container.

```shell
cookbook/assistants/run_pgvector.sh
```

## Assistant

- Basic Assistant

```shell
python cookbook/assistants/basic.py
```

## Assistants with Tools

- Data Analyst Assistant

```shell
pip install -U duckdb
```

```shell
python cookbook/assistants/data_analyst.py
```

- Web Search Assistant

```shell
pip install -U duckduckgo-search
```

```shell
python cookbook/assistants/web_search.py
```

## Assistants with Knowledge

- RAG Assistant

```shell
pip install -U sqlalchemy pgvector "psycopg[binary]"
```

```shell
python cookbook/assistants/rag_assistant.py
```

## Assistants with Memory, Knowledge and Tools

- PDF Assistant

```shell
pip install -U sqlalchemy pgvector "psycopg[binary]" pypdf
```

```shell
python cookbook/assistants/pdf_assistant.py
```
