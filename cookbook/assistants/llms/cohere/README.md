# CohereChat function calling

Currently Cohere's "command-r" and "command-r-plus" models supports function calling

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your CohereChat API Key

```shell
export CO_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U cohere duckduckgo-search yfinance exa_py phidata
```

### 4. Web search function calling

```shell
python cookbook/llms/cohere/web_search.py
```

### 5. YFinance function calling

```shell
python cookbook/llms/cohere/finance.py
```

### 6. Structured output

```shell
python cookbook/llms/cohere/structured_output.py
```

### 7. Exa Search

```shell
python cookbook/llms/cohere/exa_search.py
```
