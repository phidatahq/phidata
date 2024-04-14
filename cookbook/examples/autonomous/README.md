## Autonomous Assistant

> Fork and clone the repository if needed.

1. Start pgvector

```shell
phi start cookbook/auto/resources.py -y
```

2. Install libraries

```shell
pip install -U pgvector pypdf psycopg sqlalchemy phidata
```

3. Run Autonomous Assistant

```shell
python cookbook/auto/assistant.py
```

4. Stop pgvector

```shell
phi stop cookbook/auto/resources.py -y
```
