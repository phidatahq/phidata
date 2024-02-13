## Together

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U together phidata openai
```

3. Export `TOGETHER_API_KEY`

```text
export TOGETHER_API_KEY=<together-api-key>
```

4.Test Together Assistant

- Streaming

```shell
python cookbook/together/assistant.py
```

- Without Streaming

```shell
python cookbook/together/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/together/pydantic_output.py
```

> WARNING: function calling with together is not working

6. Test function calling

```shell
python cookbook/together/tool_call.py
```
