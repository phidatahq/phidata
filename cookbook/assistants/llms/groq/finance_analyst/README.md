# Financial Analyst with LLama3 & Groq

> This is a work in progress

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

### 3. Financial Analyst that uses OpenBB

Install libraries:

```shell
pip install "openbb[all]" polars pyarrow
```

Run using:

```shell
python cookbook/llms/groq/finance_analyst/openbb_analyst.py
```

Ask questions like:
- What's the stock price for meta
- Are analysts expecting meta to go up, share details
- What are analysts saying about NVDA

### 4. Financial Analyst that uses Yfinance

Install yfinance:

```shell
pip install yfinance
```

Run using:

```shell
python cookbook/llms/groq/finance_analyst/yfinance.py
```

Ask questions like:
- What's the NVDA stock price
- Summarize fundamentals for TSLA
