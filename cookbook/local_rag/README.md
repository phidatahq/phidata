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
pip install -r cookbook/local_rag/requirements.txt
```

### 4. Run pgvector

```shell
phi start cookbook/local_rag/resources.py -y
```

### 5. Run Streamlit application

```shell
streamlit run cookbook/local_rag/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your local AI app.
- Upload you own PDFs and ask questions
- Example PDF: https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf

### 6. Optional: Run CLI application

```shell
python cookbook/local_rag/cli.py
```

Ask questions about thai recipes

```text
Share a pad thai recipe.
```

Run CLI with a different model

```shell
python cookbook/local_rag/cli.py --model gemma:7b
```

### 7. Turn off pgvector

```shell
phi stop cookbook/local_rag/resources.py -y
```

### 8. Message me on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 9. Star ⭐️ the project if you like it.
