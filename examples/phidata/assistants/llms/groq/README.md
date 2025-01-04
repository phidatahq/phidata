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

### 3. Export GROQ API Key

```shell
export GROQ_API_KEY=***
```

### 4. Run Assistants

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

### 5. Financial analyst

Install libraries

```shell
pip install -U yfinance
```

Run using:

```shell
python cookbook/llms/groq/finance.py
```

Ask questions like:
- What's the NVDA stock price
- Summarize fundamentals for TSLA

### 6. Data analyst

Install libraries

```shell
pip install -U duckdb
```

Run using:

```shell
python cookbook/llms/groq/data_analyst.py
```

Ask questions like:
- What is the average rating of movies?
- Who is the most popular actor?
- Show me a histogram of movie ratings
