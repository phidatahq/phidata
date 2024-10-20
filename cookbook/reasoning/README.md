# Agentic Reasoning

> WARNING: Reasoning is an experimental feature and may not work as expected.

### Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### Install libraries

```shell
pip install -U openai phidata
```

### Export your `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=***
```

### Run a reasoning agent that DOES NOT WORK

```shell
python cookbook/reasoning/strawberry.py
```

### Run other examples of reasoning agents

```shell
python cookbook/reasoning/logical_puzzle.py
```

```shell
python cookbook/reasoning/ethical_dilemma.py
```

### Run reasoning agent with tools

```shell
python cookbook/reasoning/finance_agent.py
```
