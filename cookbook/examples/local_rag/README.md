# Fully Local RAG with Ollama & PgVector

> Note: Fork and clone this repository if needed

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and run models

Run you embedding model

```shell
ollama run nomic-embed-text
```

Run your chat model

```shell
ollama run openhermes
```

Message `/bye` to exit the chat model

### 2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 3. Install libraries

```shell
pip install -r cookbook/examples/local_rag/requirements.txt
```

### 4. Run PgVector

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

### 5. Run Streamlit application

```shell
streamlit run cookbook/examples/local_rag/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your local AI app.
- Upload you own PDFs and ask questions
- Example PDF: https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf

### 6. Optional: Run CLI application

```shell
python cookbook/examples/local_rag/cli.py
```

Ask questions about thai recipes

```text
Share a pad thai recipe.
```

Run CLI with a different model

```shell
python cookbook/examples/local_rag/cli.py --model gemma:7b
```

### 7. Message me on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 8. Star ⭐️ the project if you like it.
