## Pgvector Assistant

1. Run pgvector

```shell
phi start cookbook/pgvector/resources.py -y
```

2. Install libraries

```shell
pip install -U pgvector pypdf psycopg sqlalchemy
```

3. Run PgVector Assistant

```shell
python cookbook/pgvector/assistant.py
```

4. Turn off pgvector

```shell
phi stop cookbook/pgvector/resources.py -y
```
