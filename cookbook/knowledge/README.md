## Assistant Knowledge cookbooks

**Knowledge Base:** is information that the Assistant can search to improve its responses. This directory contains a series of cookbooks that demonstrate how to build a knowledge base for the Assistant.

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U openai phidata
```

3. Run PgVector

- Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) for running PgVector in a container.

```shell
phi start cookbook/knowledge/resources.py -y
```

4. Test knowledge cookbooks

Eg: PDF URL Knowledge Base

- Install libraries

```shell
pip install -U pypdf sqlalchemy pgvector 'psycopg[binary]' bs4
```

- Run the PDF URL script

```shell
python cookbook/knowledge/pdf_url.py
```

5. Stop PgVector

```shell
phi stop cookbook/knowledge/resources.py -y
```
