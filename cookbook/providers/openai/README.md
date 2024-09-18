# OpenAI Cookbook

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai phidata
```

### 4. Test Agent

```shell
python cookbook/llms/openai/basic_stream.py
```