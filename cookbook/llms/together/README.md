## Together AI

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U together openai phidata
```

3. Export `TOGETHER_API_KEY`

```text
export TOGETHER_API_KEY=***
```

4. Test Together Assistant

- Streaming

```shell
python cookbook/llms/together/assistant.py
```

- Without Streaming

```shell
python cookbook/llms/together/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/llms/together/pydantic_output.py
```

6. Test cli app

```shell
python cookbook/llms/together/cli.py
```

> WARNING: function calling with together is not working

7. Test function calling

```shell
python cookbook/llms/together/tool_call.py
```
