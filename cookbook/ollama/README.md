## Ollama

1. Run ollama model or serve ollama

```shell
ollama run llama2
```

OR

```shell
ollama serve
```

2. Install libraries

```shell
pip install -U ollama
```

3. Test Ollama Assistant

```shell
python cookbook/ollama/assistant.py
```

4. Test Structured output

```shell
python cookbook/ollama/pydantic_output.py
```

5. Test Image models

```shell
python cookbook/ollama/image.py
```

6Test Tool Calls (experimental)

```shell
python cookbook/ollama/tool_call.py
```
