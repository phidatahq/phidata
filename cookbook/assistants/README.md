# Assistants Cookbook

Phidata Assistants add memory, knowledge and tools to LLMs. Let's test out a few examples.

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U phidata openai
```

## Assistants with Tools

- Basic Assistant

```shell
python cookbook/assistants/basic.py
```

- Data Analysis Assistant

```shell
python cookbook/assistants/data_analysis.py
```

## Assistants with Knowledge

4. Run PgVector

- Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) for running PgVector in a container.

```shell
phi start cookbook/examples/pgvector/resources.py -y
```

## Assistants with Memory, Knowledge and Tools
