# Autonomous RAG with Hermes 2 Pro

> Note: Fork and clone this repository if needed

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and run models

```shell
ollama run adrienbrault/nous-hermes2pro:Q8_0 'Hey!'
```

This will run the `hermes2pro` model, respond to "Hey!" and then exit.


### 2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 3. Install libraries

```shell
pip install -r cookbook/llms/hermes2/auto_rag/requirements.txt
```

### 4. Run pgvector

```shell
phi start cookbook/llms/hermes2/auto_rag/resources.py -y
```

### 5. Run Streamlit application

```shell
streamlit run cookbook/llms/hermes2/auto_rag/app.py
```

- Open [localhost:8501](http://localhost:8501) to view the AI app.
- Upload you own PDFs and ask questions
- Example PDF: https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf

### 6. Turn off pgvector

```shell
phi stop cookbook/llms/hermes2/auto_rag/resources.py -y
```

### 7. Message me on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 8. Star ⭐️ the project if you like it.
