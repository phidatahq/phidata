# Ollama

> Note: Fork and clone this repository if needed

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and run models

Run you embedding model

```shell
ollama run nomic-embed-text
```

Run your chat model

```shell
ollama run openhermes
```

Message `/bye` to exit the chat model

### 2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 3. Install libraries

```shell
pip install -U ollama phidata
```

### 4. Test Ollama Assistant

```shell
python cookbook/llms/ollama/assistant.py
```

### 5. Test Structured output

```shell
python cookbook/llms/ollama/pydantic_output.py
```

### 6. Test Image models

```shell
python cookbook/llms/ollama/image.py
```

### 7. Test Tool Calls (experimental)

> Run`pip install -U duckduckgo-search` first

```shell
python cookbook/llms/ollama/tool_call.py
```
