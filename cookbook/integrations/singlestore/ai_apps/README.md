# SingleStore AI Apps

This cookbook shows how to build the following AI Apps with SingleStore & Phidata:

1. Research Assistant: Generate research reports about complex topics
2. RAG Assistant: Chat with Websites and PDFs

We'll use the following LLMs:

- Llama3:8B running locally using Ollama (no API key needed)
- Llama3:70B running on Groq (needs an API key)
- GPT-4 - support autonomous RAG (needs an API key)

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/integrations/singlestore/ai_apps/requirements.txt
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

- To use OpenAI GPT-4, export your OPENAI_API_KEY (get it from [here](https://platform.openai.com/api-keys))

```shell
export OPENAI_API_KEY="xxx"
```

- To use Groq, export your GROQ_API_KEY (get it from [here](https://console.groq.com/))

```shell
export GROQ_API_KEY="xxx"
```

- To use Tavily Search, export your TAVILY_API_KEY (get it from [here](https://app.tavily.com/))

```shell
export TAVILY_API_KEY="xxx"
```


### 4. Install Ollama and run local models

- [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama

- Pull the embedding model

```shell
ollama pull nomic-embed-text
```

- Pull the Llama3 and Phi3 models

```shell
ollama pull llama3

ollama pull phi3
```

### 4. Run Streamlit application

```shell
streamlit run cookbook/integrations/singlestore/ai_apps/Home.py
```

### 5 Click on the Research Assistant

Add URLs to the Knowledge Base & Generate reports.

- URL: https://www.singlestore.com/blog/singlestore-indexed-ann-vector-search/
  - Topic: SingleStore Vector Search
- URL: https://www.singlestore.com/blog/choosing-a-vector-database-for-your-gen-ai-stack/
  - Topic: How to choose a vector database
- URL: https://www.singlestore.com/blog/hybrid-search-vector-full-text-search/
  - Topic: Hybrid Search
- URL: https://www.singlestore.com/blog/singlestore-high-performance-vector-search/
  - Topic: SingleStore Vector Search Performance

### 6 Click on the RAG Assistant

Add URLs and ask questions.

- URL: https://www.singlestore.com/blog/singlestore-high-performance-vector-search/
  - Question: Tell me about SingleStore vector search performance
- URL: https://www.singlestore.com/blog/choosing-a-vector-database-for-your-gen-ai-stack/
  - Question: Help me choose a vector database
- URL: https://www.singlestore.com/blog/hybrid-search-vector-full-text-search/
  - Question: Tell me about hybrid search in SingleStore?

### 7. Message us on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 8. Star ⭐️ the project if you like it.

### 9. Share this cookbook using: https://git.new/s2-phi
