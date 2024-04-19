# Groq AI

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -U groq phidata
```

### 3. Run Assistants

- basic

```shell
python cookbook/llms/groq/basic.py
```

- web search

```shell
python cookbook/llms/groq/assistant.py
```

- structured output

```shell
python cookbook/llms/groq/structured_output.py
```

### 4. Financial analyst

Run using:

```shell
python cookbook/llms/groq/finance.py
```

Ask questions like:
- What's the NVDA stock price
- Summarize fundamentals for TSLA
