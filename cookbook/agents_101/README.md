# Agents 101

Here we have a basic walkthrough of a basic to more advanced agent.

The cookbooks are organised as follows:
 - [Get started](./agents_101): A basic series of agents to get you started.
 - [Advanced examples](./advanced_examples): Interesting use-cases and complex agents and RAG examples.
 - [Playground / Agent UI](./playground): Run a playground app and view it on the Agno Agent UI.
 - [Agent concepts](./agent_concepts): General agent concepts.
 - [Knowledge bases](./knowledge): All about agent knowledge bases.
 - [Models](./models): All the model providers and the various features supported via Agno.
 - [Tools](./tools): All the tools supported via Agno.
 - [VectorDBs](./vector_dbs): Agent VectorDB examples.
 - [Workflows](./workflows): Examples of workflows and a script to run them as a playground app.


## Setup

### Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### Install libraries

```shell
pip install -U openai phidata  # And all other packages you might need
```

### Export your keys

```shell
export OPENAI_API_KEY=***
export GOOGLE_API_KEY=***
```

## Run a cookbook

```shell
python cookbook/.../example.py
```
