# OpenAI Cookbook

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai phidata duckduckgo-search
```

### 4. Test Assistant

```shell
python cookbook/llms/openai/assistant.py
```

### 5. Test structured output

```shell
python cookbook/llms/openai/pydantic_output.py
```

### 6. Test finance Assistant

- Install `yfinance` using `pip install yfinance`

- Run the finance assistant

```shell
python cookbook/llms/openai/finance.py
```
