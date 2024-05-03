# Autonomous RAG with GPT4

This cookbook shows how to do Autonomous retrieval-augmented generation with GPT4.

Auto-RAG is just a fancy name for giving the LLM tools like "search_knowledge_base", "read_chat_history", "search_the_web"
and letting it decide how to retrieve the information it needs to answer the question.

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=***
```

### 4. Install libraries

```shell
pip install -r cookbook/llms/openai/auto_rag/requirements.txt
```

### 5. Run PgVector

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

### 6. Run Autonomous RAG App

```shell
streamlit run cookbook/llms/openai/auto_rag/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your RAG app.
- Add websites or PDFs and ask question.

- Example Website: https://techcrunch.com/2024/04/18/meta-releases-llama-3-claims-its-among-the-best-open-models-available/
- Ask questions like:
  - What did Meta release?
  - Tell me more about the Llama 3 models?

### 7. Message on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 8. Star ⭐️ the project if you like it.
