# Agentic RAG

**RAG:** is a technique that allows an Agent to search for information to improve its responses. This directory contains a series of cookbooks that demonstrate how to build a RAG for the Agent.

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -U openai sqlalchemy "psycopg[binary]" pgvector lancedb tantivy pypdf sqlalchemy "fastapi[standard]" phidata
```

### 3. Run PgVector

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

### 4. Run the Traditional RAG with PgVector

```shell
python cookbook/rag/01_traditional_rag_pgvector.py
```

### 5. Run the Agentic RAG with PgVector

```shell
python cookbook/rag/02_agentic_rag_pgvector.py
```

### 6. Run the Traditional RAG with LanceDB

```shell
python cookbook/rag/03_traditional_rag_lancedb.py
```

### 7. Run the Agentic RAG with LanceDB

```shell
python cookbook/rag/04_agentic_rag_lancedb.py
```

### 8. Run the Agentic RAG on Agent UI

```shell
python cookbook/rag/05_agentic_rag_agent_ui.py
```