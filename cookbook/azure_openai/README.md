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
export AZURE_OPENAI_API_KEY=<azure-api-key>
export AZURE_OPENAI_ENDPOINT=<azure-endpoint>
# Optional:
# export AZURE_OPENAI_API_VERSION=<openai-api-version>
# export AZURE_DEPLOYMENT=<azure_deployment>
```

4. Test Azure Assistant

- Streaming

```shell
python cookbook/azure/assistant.py
```

- Without Streaming

```shell
python cookbook/azure/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/azure/pydantic_output.py
```

6. Test cli app

```shell
python cookbook/azure/cli.py
```

7. Test function calling

```shell
python cookbook/azure/tool_call.py
```
