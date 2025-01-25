# SQL Agent

This cookbook showcases a SQL Agent that can write and run SQL queries.
It uses RAG to provide additional information and rules that can be used to improve the responses.

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/examples/streamlit/sql/requirements.txt
```

### 3. Run PgVector

We use Postgres as a database to demonstrate the SQL Agent.

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
  agnohq/pgvector:16
```

For best results, `table_rules` and `column_rules` to the JSON. The Agent is prompted to follow them.
This is useful when you want to guide the Agent  to always query date, use a particular format, or avoid certain columns.

You are also free to add sample SQL queries to the `cookbook/examples/streamlit/sql/knowledge_base/sample_queries.sql` file.
This will give the Assistant a head start on how to write complex queries.

> After testing with the f1 knowledge, you should update this file to load your own knowledge.

### 4. Export OpenAI API Key

> You can use any Model you like, this is a complex task so best suited for GPT-4o or similar models.

```shell
export OPENAI_API_KEY=***
```

### 5. Run SQL Agent

```shell
streamlit run cookbook/examples/streamlit/sql/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your SQL Assistant.

### 6. Message on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

