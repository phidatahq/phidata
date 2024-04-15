## RAG Assistant

> Fork and clone the repository if needed.

1. Start pgvector

```shell
phi start cookbook/examples/rag/resources.py -y
```

2. Install libraries

```shell
pip install -U pgvector pypdf psycopg sqlalchemy phidata
```

3. Run RAG Assistant

```shell
python cookbook/examples/rag/assistant.py
```

4. Stop pgvector

```shell
phi stop cookbook/examples/rag/resources.py -y
```
