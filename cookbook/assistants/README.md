# Assistants Cookbook

Phidata Assistants add memory, knowledge and tools to LLMs. Let's test out a few examples.

- Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

- Install libraries

```shell
pip install -U phidata openai
```

## Assistants

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

- Python Assistant

```shell
python cookbook/assistants/python_assistant.py
```

## Run PgVector

> Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) first.

- Run using a helper script

```shell
./cookbook/run_pgvector.sh
```

- OR run using the docker run command

```shell
docker run -d \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 \
  --name pgvector \
  phidata/pgvector:16
```

## Assistants with Knowledge

- Install libraries

```shell
pip install -U sqlalchemy pgvector "psycopg[binary]" pydpdf
```

- RAG Assistant

```shell
python cookbook/assistants/rag_assistant.py
```

- Autonomous Assistant

```shell
python cookbook/assistants/auto_assistant.py
```

## Assistants with Storage, Knowledge & Tools

- PDF Assistant

```shell
python cookbook/assistants/pdf_assistant.py
```
