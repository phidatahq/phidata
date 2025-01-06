# AI Research Workflow

We've created a constrained AI Research Workflow that uses Agents to writes a detailed blog on topic by utilizing LLM models and external tools:
- Exa
- ArXiv

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install requirements

```shell
pip install -r cookbook/examples/agents/research_agent_app/requirements.txt
```

### 3. Export `OPENAI_API_KEY` and `EXA_API_KEY`

```shell
export OPENAI_API_KEY=sk-***
export EXA_API_KEY=***
```

### 4. Run Streamlit App

```shell
streamlit run cookbook/examples/agents/research_agent_app/app.py
```
