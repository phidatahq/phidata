## DeepSeek

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv venv
source venv/bin/activate
```

2. Install libraries

```shell
pip install -U openai phidata
```

3. Export `DEEPSEEK_API_KEY`

```shell
export DEEPSEEK_API_KEY=***
```

4. Test Structured output

```shell
python cookbook/llms/deepseek/pydantic_output.py
```

5. Test function calling

```shell
python cookbook/llms/deepseek/tool_call.py
```
