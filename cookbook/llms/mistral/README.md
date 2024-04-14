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
export MISTRAL_API_KEY=xxx
```

3. Install libraries

```shell
pip install -r cookbook/llms/mistral/requirements.txt
```

4. Start pgvector

```shell
phi start cookbook/llms/mistral/resources.py -y
```

5. Run RAG App

```shell
streamlit run cookbook/llms/mistral/app.py
```

6. Stop pgvector

```shell
phi stop cookbook/llms/mistral/resources.py -y
```

## Build AI Assistants with Mistral

1. Install libraries

```shell
pip install -U mistralai phidata
```

2. Run Assistant

```shell
python cookbook/llms/mistral/simple_assistant.py
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
