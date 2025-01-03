## Pgvector Agent

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -U qdrant-client pypdf openai phidata
```

### 3. Run Qdrant

```shell
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant
```

### 4. Run Qdrant Agent

```shell
python cookbook/integrations/qdrant/agent.py
```
