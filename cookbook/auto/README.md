## Autonomous Assistant

1. Run pgvector

```shell
phi start cookbook/auto/resources.py -y
```

2. Install libraries

```shell
pip install -U pgvector pypdf psycopg sqlalchemy
```

3. Run RAG Assistant

```shell
python cookbook/auto/assistant.py
```

4. Turn off pgvector

```shell
phi stop cookbook/auto/resources.py -y
```
