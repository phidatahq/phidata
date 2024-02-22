# OpenHermes & Ollama

> Note: Fork and clone this repository if needed

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and run openhermes

```shell
ollama run openhermes
```

send `/bye` to exit the chat interface

### 2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 3. Install libraries

```shell
pip install -U ollama phidata
```

### 4. Test Completion

```shell
python cookbook/openhermes/assistant.py
```

### 5. Test Structured output

```shell
python cookbook/openhermes/pydantic_output.py
```

### 6. Test Tool Calls (experimental)

> Run`pip install -U duckduckgo-search` first

```shell
python cookbook/openhermes/tool_call.py
```

### 7. Test Embeddings

```shell
python cookbook/openhermes/embeddings.py
```
