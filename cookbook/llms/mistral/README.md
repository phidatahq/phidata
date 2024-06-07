# Mistral AI

> Note: Fork and clone this repository if needed

1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Export your Mistral API Key

```shell
export MISTRAL_API_KEY=***
```

3. Install libraries

```shell
pip install -U mistralai phidata
```

2. Run Assistant

```shell
python cookbook/llms/mistral/assistant.py
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
