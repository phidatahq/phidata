## Together

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U together phidata
```

3. Test Together Assistant

- Streaming

```shell
python cookbook/together/assistant.py
```

- Without Streaming

```shell
python cookbook/together/assistant_stream_off.py
```

4. Test Structured output

```shell
python cookbook/together/pydantic_output.py
```

5. Test function calling

```shell
python cookbook/together/tool_call.py
```
