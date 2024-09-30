# Investment Researcher

This cookbook contains an Investment Researcher that generates an investment report on a stock.

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/llms/groq/investment_researcher/requirements.txt
```

### 3. Export your Groq API Key

```shell
export GROQ_API_KEY=***
```

### 4. Run Investment Researcher

```shell
streamlit run cookbook/llms/groq/investment_researcher/app.py
```

Provide tickers for research and click on the `Generate Report` button to generate the investment report.
Example: `NVDA, AAPL, MSFT, GOOGL, AMZN, TSLA`

### 5. Message us on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 6. Star ⭐️ the project if you like it.

### 7. Share with your friends: https://git.new/groq-investor
