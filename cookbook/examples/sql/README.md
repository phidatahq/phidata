# SQL Assistant

This cookbook showcases a SQL Assistant that can write and run SQL queries.
It uses RAG to provide additional information and rules that can be used to improve the responses.

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/examples/sql/requirements.txt
```

### 3. Run PgVector

We use Postgres as a database to demonstrate the SQL Assistant.

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

### 4. Load F1 Data

```shell
python cookbook/examples/sql/load_f1_data.py
```

> After testing with f1 data, you should update this file to load your own data.

### 5. Load Knowledge Base

The SQL Assistant works best when you provide it knowledge about the tables and columns in the database.
While you're free to let it go rogue on your database, this is a way for us to provide rules and instructions that
it must follow.

```shell
python cookbook/examples/sql/load_knowledge.py
```

For best results, `table_rules` and `column_rules` to the JSON. The Assistant is prompted to follow them.
This is useful when you want to guide the Assistant to always query date, use a particular format, or avoid certain columns.

You are also free to add sample SQL queries to the `cookbook/examples/sql/knowledge_base/sample_queries.sql` file.
This will give the Assistant a head start on how to write complex queries.

> After testing with the f1 knowledge, you should update this file to load your own knowledge.

### 4. Export OpenAI API Key

> You can use any LLM you like, this is a complex task so best suited for GPT-4.

```shell
export OPENAI_API_KEY=***
```

### 5. Run SQL Assistant

```shell
streamlit run cookbook/examples/sql/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your SQL Assistant.

### 6. Message on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 7. Share with your friends: https://git.new/sql-ai
