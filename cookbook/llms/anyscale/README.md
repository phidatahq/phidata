## Anyscale Endpoints

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U openai phidata
```

3. Export `ANYSCALE_API_KEY`

```shell
export ANYSCALE_API_KEY=***
```

4. Test Anyscale Assistant

- Streaming

```shell
python cookbook/llms/anyscale/assistant.py
```

- Without Streaming

```shell
python cookbook/llms/anyscale/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/llms/anyscale/pydantic_output.py
```

6. Test function calling

```shell
python cookbook/llms/anyscale/tool_call.py
```
