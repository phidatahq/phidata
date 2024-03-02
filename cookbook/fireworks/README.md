## Fireworks AI

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

3. Export `FIREWORKS_API_KEY`

```text
export FIREWORKS_API_KEY=<fireworks-api-key>
```

4. Test Fireworks Assistant

- Streaming

```shell
python cookbook/fireworks/assistant.py
```

- Without Streaming

```shell
python cookbook/fireworks/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/fireworks/pydantic_output.py
```

6. Test function calling

```shell
python cookbook/fireworks/tool_call.py
```

```shell
python cookbook/fireworks/web_search.py
```
