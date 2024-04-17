# Groq AI

> Note: Fork and clone this repository if needed

## RAG AI App with Groq & PgVector

1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Export your Groq & OpenAI API Key

> Need to use OpenAI for embeddings as Groq doesn't support embeddings yet.

```shell
export GROQ_API_KEY=***
export OPENAI_API_KEY=sk-***
```

3. Install libraries

```shell
pip install -r cookbook/llms/groq/requirements.txt
```

4. Start pgvector

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

5. Run RAG App

```shell
streamlit run cookbook/llms/groq/app.py
```

## Build AI Assistants with Groq

1. Install libraries

```shell
pip install -U groq phidata
```

2. Run Assistant

```shell
python cookbook/llms/groq/assistant.py
```
