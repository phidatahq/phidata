# Cohere function calling

Currently "command-r" model supports function calling

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your Cohere API Key

```shell
export CO_API_KEY=xxx
```

### 3. Install libraries

```shell
pip install -U cohere phidata duckduckgo-search yfinance exa_py
```

### 4. Web search function calling

```shell
python cookbook/cohere/web_search.py
```

### 5. YFinance function calling

```shell
python cookbook/cohere/finance.py
```

### 6. Structured output

```shell
python cookbook/cohere/structured_output.py
```

### 7. Exa Search

```shell
python cookbook/cohere/exa_search.py
```
