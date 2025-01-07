# Agno Cookbooks

Here you’ll find examples that’ll help you use Agno, from basic agents and workflows to advanced multi-agent examples.
If you have more, please contribute to this list.

The cookbooks are organised as follows:
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
