## Fireworks AI Function Calling

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U openai yfinance exa_py duckduckgo-search streamlit phidata
```

3. Export `FIREWORKS_API_KEY`

```text
export FIREWORKS_API_KEY=<fireworks-api-key>
```

> If you want to use Exa Search, export `EXA_API_KEY` as well

```text
export EXA_API_KEY=<exa-api-key>
```

4. Run streamlit app

```shell
streamlit run cookbook/fireworks/app.py
```

---

5. Test Fireworks Assistant

- Streaming

```shell
python cookbook/fireworks/assistant.py
```

- Without Streaming

```shell
python cookbook/fireworks/assistant_stream_off.py
```

6. Test Structured output

```shell
python cookbook/fireworks/pydantic_output.py
```

7. Test function calling

```shell
python cookbook/fireworks/tool_call.py
```

```shell
python cookbook/fireworks/web_search.py
```
