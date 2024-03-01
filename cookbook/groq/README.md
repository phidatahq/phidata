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
export GROQ_API_KEY=xxx
export OPENAI_API_KEY=sk-***
```

3. Install libraries

```shell
pip install -r cookbook/groq/requirements.txt
```

4. Start pgvector

```shell
phi start cookbook/groq/resources.py -y
```

5. Run RAG App

```shell
streamlit run cookbook/groq/app.py
```

6. Stop pgvector

```shell
phi stop cookbook/groq/resources.py -y
```

## Build AI Assistants with Groq

1. Install libraries

```shell
pip install -U groq phidata
```

2. Run Assistant

- stream on

```shell
python cookbook/groq/assistant.py
```

- stream off

```shell
python cookbook/groq/assistant_stream_off.py
```
