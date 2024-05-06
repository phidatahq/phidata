## OpenRouter

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

3. Export `OPENROUTER_API_KEY`

```shell
export OPENROUTER_API_KEY=***
```

4. Test OpenRouter Assistant

- Streaming

```shell
python cookbook/llms/openrouter/assistant.py
```

- Without Streaming

```shell
python cookbook/llms/openrouter/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/llms/openrouter/pydantic_output.py
```

6. Test function calling

```shell
python cookbook/llms/openrouter/tool_call.py
```
