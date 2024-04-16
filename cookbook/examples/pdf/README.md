# PDF Assistant with knowledge and storage

> Note: Fork and clone this repository if needed

Lets create a PDF Assistant that can answer questions from a PDF. We'll use `PgVector` for knowledge and storage.

**Knowledge Base:** information that the Assistant can search to improve its responses (uses a vector db).

**Storage:** provides long term memory for Assistants (uses a database).

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -U pgvector pypdf "psycopg[binary]" sqlalchemy openai phidata
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

### 4. Run PDF Assistant

```shell
python cookbook/examples/pdf/assistant.py
```

- Ask a question:

```
How do I make pad thai?
```

- See how the Assistant searches the knowledge base and returns a response.

- Message `bye` to exit, start the assistant again using `python cookbook/examples/pdf/assistant.py` and ask:

```
What was my last message?
```

- Run the `assistant.py` file with the `--new` flag to start a new run.

```shell
python cookbook/examples/pdf/assistant.py --new
```
