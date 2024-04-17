# Mistral AI

> Note: Fork and clone this repository if needed

## RAG AI App with Mistral & PgVector

1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Export your Mistral API Key

```shell
export MISTRAL_API_KEY=***
```

3. Install libraries

```shell
pip install -r cookbook/llms/mistral/requirements.txt
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
streamlit run cookbook/llms/mistral/app.py
```

## Build AI Assistants with Mistral

1. Install libraries

```shell
pip install -U mistralai phidata
```

2. Run Assistant

```shell
python cookbook/llms/mistral/assistant.py
```

3. Output Pydantic models

```shell
python cookbook/llms/mistral/pydantic_output.py
```

4. Run Assistant with Tool calls

> NOTE: currently not working

```shell
pip install duckduckgo-search

python cookbook/llms/mistral/tool_call.py
```

Optional: View Mistral models

```shell
python cookbook/llms/mistral/list_models.py
```
