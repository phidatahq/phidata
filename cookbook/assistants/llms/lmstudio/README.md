## LM Studio

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

3. Make sure [LM Studio](https://lmstudio.ai/) is installed and the Local Inference Server is running.

4. Test Assistant

- Streaming

```shell
python cookbook/llms/lmstudio/assistant.py
```

- Without Streaming

```shell
python cookbook/llms/lmstudio/assistant_stream_off.py
```

5. Test Structured output

```shell
python cookbook/llms/lmstudio/pydantic_output.py
```

6. Test function calling

```shell
python cookbook/llms/lmstudio/tool_call.py
```
