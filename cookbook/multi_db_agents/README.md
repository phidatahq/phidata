### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai pydruid psycopg2 'fastapi[standard]' phidata
```

### 4. Run the Agent UI

```shell
streamlit run cookbook/multi_db_agents/multi_agent.py
```
