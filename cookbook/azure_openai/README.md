## Azure OpenAI

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U azure_openai phidata openai, azureChatGPT
```

3. Export `AZURE_OPENAI_API_KEY` </br>
   Export `OPENAI_API_VERSION`</br>
   Export `AZURE_OPENAI_ENDPOINT`</br>
   Export `AZURE_DEPLOYMENT`

```text
export AZURE_OPENAI_API_KEY=<azure_openai-api-key>
export OPENAI_API_VERSION=<openai-api-version>
export AZURE_OPENAI_ENDPOINT=<azure_openai-endpoint>
export AZURE_DEPLOYMENT=<azure_deployment>
```

4. Test AzureChatGPT Assistant

- Streaming

```shell
python cookbook/azure_openai/assistant.py
```

- Without Streaming

```shell
python cookbook/azure_openai/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/azure_openai/pydantic_output.py
```

6. Test cli app

```shell
python cookbook/azure_openai/cli.py
```

7. Test function calling

```shell
python cookbook/azure_openai/tool_call.py
```
