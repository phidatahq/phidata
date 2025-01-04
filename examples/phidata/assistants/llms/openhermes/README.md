# OpenHermes Cookbook

OpenHermes is a 7B model fine-tuned by Teknium on Mistral with fully open datasets.
Personal experience shows that OpenHermes perfoms spectacularly well on a wide range of tasks.
Follow this cookbook to get test OpenHermes yourself.

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

### 4. Test Generation

```shell
python cookbook/llms/openhermes/assistant.py
```

### 5. Test Structured output

```shell
python cookbook/llms/openhermes/pydantic_output.py
```

### 6. Test Tool Calls (experimental)

> Run`pip install -U duckduckgo-search` first

```shell
python cookbook/llms/openhermes/tool_call.py
```

### 7. Test Embeddings

```shell
python cookbook/llms/openhermes/embeddings.py
```
