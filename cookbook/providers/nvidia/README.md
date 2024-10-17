# Nvidia Cookbook

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `NVIDIA_API_KEY`

```shell
export NVIDIA_API_KEY=***
```

### 3. Install libraries

```shell
pip install -U openai phidata
```

### 4. Run Agent without Tools

- Streaming on

```shell
python cookbook/providers/nvidia/basic_stream.py
```

- Streaming off

```shell
python cookbook/providers/nvidia/basic.py
```
## Disclaimer:

nvidia/llama-3.1-nemotron-70b-instruct does not support function calling.
