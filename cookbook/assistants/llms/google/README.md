# Google Gemini Cookbook

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export `GOOGLE_API_KEY`

```shell
export GOOGLE_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U google-generativeai duckduckgo-search phidata
```

### 4. Test Assistant

```shell
python cookbook/llms/google/assistant.py
```

### 5. Test structured output

```shell
python cookbook/llms/google/pydantic_output.py
```

### 6. Test finance Assistant

- Install `yfinance` using `pip install yfinance`

- Run the finance assistant

```shell
python cookbook/llms/google/finance.py
```
