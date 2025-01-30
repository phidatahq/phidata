# Data Visualization Agent

Let's build a Data Visualization Agent .


> Note: Fork and clone the repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/examples/apps/data_visualization/requirements.txt
```

### 3. Run PgVector

Let's use Postgres for storing our data, but the SQL Agent should work with any database.

> Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) first.

- Run using a helper script

```shell
./cookbook/scripts/run_pgvector.sh
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


### 4. Export API Keys

We recommend using gpt-4o for this task, but you can use any Model you like.

```shell
export OPENAI_API_KEY=***
```



### 5. Run Data Visualization Agent

```shell
streamlit run cookbook/examples/apps/data_visualization/app.py
```

- Open [localhost:8501](http://localhost:8501) to view the Data Visualization Agent.

### 6. Message us on [discord](https://agno.link/discord) if you have any questions

