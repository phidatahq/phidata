# Hermes 2 Pro Function Calling and JSON Structured Outputs

Hermes 2 Pro is the new flagship 7B Hermes that maintains its excellent general task and conversation capabilities
but also excels at Function Calling, JSON Structured Outputs, and has improved on several other metrics as well,
scoring a 90% on the function calling evaluation built in partnership with Fireworks.AI,
and an 81% on the structured JSON Output evaluation.

> Note: Fork and clone this repository if needed

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and run hermes2pro

```shell
ollama run adrienbrault/nous-hermes2pro:Q8_0 'Hey!'
```

This will run the `hermes2pro` model, respond to "Hey!" and then exit.

### 2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 3. Install libraries

```shell
pip install -U ollama duckduckgo-search yfinance phidata
```

### 4. Web search function calling

```shell
python cookbook/llms/hermes2/web_search.py
```

### 5. YFinance function calling

```shell
python cookbook/llms/hermes2/finance.py
```

### 6. Structured output

```shell
python cookbook/llms/hermes2/structured_output.py
```

### 7. Exa Search

```shell
pip install -U exa_py bs4

python cookbook/llms/hermes2/exa_kg.py
```

### 8. Test Embeddings

```shell
python cookbook/llms/hermes2/embeddings.py
```
