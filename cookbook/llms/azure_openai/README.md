# Azure OpenAI

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U phidata openai
```

3. Export Azure Credentials (`AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` are required)

```shell
export AZURE_OPENAI_API_KEY=***
export AZURE_OPENAI_ENDPOINT=***
# Optional:
# export AZURE_OPENAI_API_VERSION=***
# export AZURE_DEPLOYMENT=***
```

4. Test Azure Assistant

- Streaming

```shell
python cookbook/llms/azure/assistant.py
```

- Without Streaming

```shell
python cookbook/llms/azure/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/llms/azure/pydantic_output.py
```

6. Test cli app

```shell
python cookbook/llms/azure/cli.py
```

7. Test function calling

```shell
python cookbook/llms/azure/tool_call.py
```
