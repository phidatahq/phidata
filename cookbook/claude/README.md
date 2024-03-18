# Claude 

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your Anthropic API Key

```shell
export ANTHROPIC_API_KEY=xxx
```

### 3. Install libraries

```shell
pip install -r cookbook/claude/requirements.txt
```

### 4. Web search function calling

```shell
python cookbook/claude/web_search.py
```

### 5. YFinance function calling

```shell
python cookbook/claude/finance.py
```

### 6. Structured output

```shell
python cookbook/claude/structured_output.py
```
