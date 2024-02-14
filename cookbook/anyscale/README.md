## Anyscale Endpoints

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

3. Export `ANYSCALE_API_KEY`

```text
export ANYSCALE_API_KEY=<anyscale-api-key>
```

4. Test Anyscale Assistant

- Streaming

```shell
python cookbook/anyscale/assistant.py
```

- Without Streaming

```shell
python cookbook/anyscale/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/anyscale/pydantic_output.py
```

6. Test function calling

```shell
python cookbook/anyscale/tool_call.py
```
