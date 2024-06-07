# Llama Cpp

This cookbook shows how to build Assistants using [Llama.cpp](https://github.com/ggerganov/llama.cpp).

> Note: Fork and clone this repository if needed

1. Download a model from huggingface and store in the `./models` directory.

For example download `openhermes-2.5-mistral-7b.Q8_0.gguf` from https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/tree/main

> The `./models` directory is ignored using .gitignore

2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/llamaenv
source ~/.venvs/llamaenv/bin/activate
```

3. Install libraries

```shell
pip install -U phidata 'llama-cpp-python[server]'
```

4. Run the server

```shell
python3 -m llama_cpp.server --model cookbook/llms/llama_cpp/models/openhermes-2.5-mistral-7b.Q8_0.gguf
```

5. Test LLama Assistant

- Streaming

```shell
python cookbook/llms/llama_cpp/assistant.py
```

- Without Streaming

```shell
python cookbook/llms/llama_cpp/assistant_stream_off.py
```

6. Test Structured output

```shell
python cookbook/llms/llama_cpp/pydantic_output.py
```

7. Test function calling

```shell
python cookbook/llms/llama_cpp/tool_call.py
```
