# Groq AI Apps

This cookbook shows how to build the following AI Apps with Groq:

1. RAG Research: Generate research reports about complex topics
2. RAG Chat: Chat with Websites and PDFs

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/llms/groq/ai_apps/requirements.txt
```

### 3. Export your Groq API Key

```shell
export GROQ_API_KEY=***
```

- The Research Assistant can parse Websites and PDFs, but if you want to us Tavily Search as well, export your TAVILY_API_KEY (get it from [here](https://app.tavily.com/))

```shell
export TAVILY_API_KEY=xxx
```

### 4. Install Ollama to run the local embedding model

Groq currently does not support embeddings, so lets use Ollama to serve embeddings using `nomic-embed-text`

- [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama

- Pull the embedding model

```shell
ollama pull nomic-embed-text
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

### 6. Run Streamlit application

```shell
streamlit run cookbook/llms/groq/ai_apps/Home.py
```

### 7. Click on the RAG Research Assistant

Add URLs and PDFs to the Knowledge Base & Generate reports.

Examples:
- URL: https://techcrunch.com/2024/04/18/meta-releases-llama-3-claims-its-among-the-best-open-models-available/
  - Topic: Llama 3
- URL: https://www.singlestore.com/blog/choosing-a-vector-database-for-your-gen-ai-stack/
  - Topic: How to choose a vector database

- PDF: Download the embeddings PDF from [https://vickiboykis.com/what_are_embeddings/](https://vickiboykis.com/what_are_embeddings/)
  - Topic: Embeddings

### 8. Click on the RAG Chat Assistant

Add URLs and PDFs and ask questions.

Examples:
- URL: https://techcrunch.com/2024/04/18/meta-releases-llama-3-claims-its-among-the-best-open-models-available/
  - Question: What did Meta release?
- URL: https://www.singlestore.com/blog/choosing-a-vector-database-for-your-gen-ai-stack/
  - Question: Help me choose a vector database

### 9. Message us on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 10. Star ⭐️ the project if you like it.
