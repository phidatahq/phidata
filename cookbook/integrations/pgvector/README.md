## Pgvector Assistant

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
phi start cookbook/integrations/pgvector/resources.py -y
```

4. Run PgVector Assistant

```shell
python cookbook/integrations/pgvector/assistant.py
```

5. Turn off pgvector

```shell
phi stop cookbook/integrations/pgvector/resources.py -y
```
