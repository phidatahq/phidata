# Medical Research Team

Inspired by the fantastic work by [Matt Shumer (@mattshumer_)](https://twitter.com/mattshumer_/status/1772286375817011259).
We created a constrained Medical Research Team that uses GPT-4 Assistants to write a report.

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install openai arxiv exa_py phidata pypdf
```

### 3. Export `OPENAI_API_KEY` and `EXA_API_KEY`

```shell
export OPENAI_API_KEY=sk-***
export EXA_API_KEY=***
```

### 4. Run the Research Team to generate an report

```shell
python cookbook/teams/medical_research/generate_report.py
```
