## SQL Assistant

This cookbook showcases a SQL Assistant that can write and run SQL queries.
It uses RAG to provide additional information and rules that can be used to improve the responses.

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U pgvector pypdf psycopg[binary] sqlalchemy openai phidata
```

3. Run PgVector

- Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) for running PgVector in a container.

```shell
phi start cookbook/examples/pgvector/resources.py -y
```

4. Run PgVector Assistant

```shell
python cookbook/examples/pgvector/assistant.py
```

5. Turn off pgvector

```shell
phi stop cookbook/examples/pgvector/resources.py -y
```
