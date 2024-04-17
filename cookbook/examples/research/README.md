# AI Research Team

Inspired by the fantastic work by [Matt Shumer (@mattshumer_)](https://twitter.com/mattshumer_/status/1772286375817011259).
We've created a constrained Research Team that uses GPT-4 Assistants to write a report by searching:
- DuckDuckGo
- Exa
- ArXiv

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install requirements

```shell
pip install -r cookbook/examples/research/requirements.txt
```

### 3. Export `OPENAI_API_KEY` and `EXA_API_KEY`

```shell
export OPENAI_API_KEY=sk-***
export EXA_API_KEY=***
```

### 4. Run Streamlit App

```shell
streamlit run cookbook/examples/research/app.py
```
