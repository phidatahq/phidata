# Local Function Calling with Ollama

This cookbook shows how to do function calling with local models.

> Note: Fork and clone this repository if needed

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and pull models

Pull the LLM you'd like to use:

```shell
ollama pull adrienbrault/nous-hermes2pro-llama3-8b:q8_0

ollama pull llama3
```

### 2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 3. Install libraries

```shell
pip install -r cookbook/llms/ollama/tools/requirements.txt
```

### 4. Run Function Calling App

```shell
streamlit run cookbook/llms/ollama/tools/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your local RAG app.
- Select your model.
- Ask questions like:
  - Whats NVDA stock price?
  - What are analysts saying about TSLA?
  - Summarize fundamentals for TSLA?

### 5. Message on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 6. Star ⭐️ the project if you like it.

### 7. Share with your friends: https://git.new/ollama-tools
