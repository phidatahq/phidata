# Autonomous RAG with SingleStore and Phidata

This cookbook shows how to build an Autonomous RAG application with SingleStore and Phidata.

We'll use the following LLMs:

- GPT-4 by OpenAI (needs an API key)
- Hermes2 running locally using Ollama (no API key needed)

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/integrations/singlestore/auto_rag/requirements.txt
```

### 3. Add credentials

- For SingleStore

> Note: If using a shared tier, please provide a certificate file for SSL connection [Read more](https://docs.singlestore.com/cloud/connect-to-your-workspace/connect-with-mysql/connect-with-mysql-client/connect-to-singlestore-helios-using-tls-ssl/)

```shell
export SINGLESTORE_HOST="host"
export SINGLESTORE_PORT="3333"
export SINGLESTORE_USERNAME="user"
export SINGLESTORE_PASSWORD="password"
export SINGLESTORE_DATABASE="db"
export SINGLESTORE_SSL_CA=".certs/singlestore_bundle.pem"
```

- To use OpenAI GPT-4, provide your OPENAI_API_KEY

```shell
export OPENAI_API_KEY="sk-..."
```

### Optional: To use a local model, install and run Ollama

- [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama

- Run you embedding model

```shell
ollama run nomic-embed-text
```

- Run your chat model

```shell
ollama run adrienbrault/nous-hermes2pro:Q8_0 'Hey!'
```

### 4. Run Streamlit application

```shell
streamlit run cookbook/integrations/singlestore/auto_rag/app.py
```

### 5. Provide a web page URL and ask questions

Examples:

URL: https://www.singlestore.com/blog/choosing-a-vector-database-for-your-gen-ai-stack/

Question: Help me choose a vector database

URL: https://www.singlestore.com/blog/hybrid-search-vector-full-text-search/

Question: Tell me about hybrid search in SingleStore?

URL: https://www.singlestore.com/blog/singlestore-vector-data-type-support/

Question: Tell me about vector type in SingleStore?

### 6. Message us on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 7. Star ⭐️ the project if you like it.
