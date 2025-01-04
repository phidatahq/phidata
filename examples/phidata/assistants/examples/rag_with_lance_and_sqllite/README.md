# RAG Assistant With LanceDB and SQLite

> Fork and clone the repository if needed.

## 1. Setup Ollama models

```shell
ollama pull llama3:8b
ollama pull nomic-embed-text
```

## 2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

## 3. Install libraries

```shell
!pip install -U phidata ollama lancedb pandas sqlalchemy
```

## 4. Run RAG Assistant

```shell
python cookbook/examples/rag_with_lance_and_sqllite/assistant.py
```
