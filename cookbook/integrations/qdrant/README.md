## Pgvector Agent

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -U pinecone-client pypdf openai phidata
```

### 3. Run Pinecone Agent

```shell
python cookbook/integrations/pinecone/agent.py
```
