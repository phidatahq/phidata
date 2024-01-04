<h1 align="center">
  phidata
</h1>
<h3 align="center">
  Build, ship and monitor AI products
</h3>
<p align="center">
<a href="https://python.org/pypi/phidata" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/pypi/v/phidata?color=blue&label=version" alt="version">
</a>
<a href="https://github.com/phidatahq/phidata" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/python->=3.9-blue" alt="pythonversion">
</a>
<a href="https://github.com/phidatahq/phidata" target="_blank" rel="noopener noreferrer">
    <img src="https://pepy.tech/badge/phidata" alt="downloads">
</a>
<a href="https://github.com/phidatahq/phidata/actions/workflows/build.yml" target="_blank" rel="noopener noreferrer">
    <img src="https://github.com/phidatahq/phidata/actions/workflows/build.yml/badge.svg" alt="build-status">
</a>
</p>


## ✨ What is phidata?

Phidata is an open source toolkit for building AI products. It provides a paved-path for building AI products using pre-built AI Apps that you can run locally using docker or deploy to AWS.

## 🎖 Use it to build

- **AI Apps** (RAG, autonomous or multimodal applications)
- **AI Assistants** (automate data engineering, python or snowflake tasks)
- **Rest Apis** (with FastApi, PostgreSQL)
- **Web Apps** (with Django, PostgreSQL)
- **Data Platforms** (with Airflow, Superset, Jupyter)

## 💡 What you get

**Production ready codebases** built with:

- **Building blocks** like conversations, agents, knowledge bases defined as pydantic objects
- **Applications** like FastApi, Streamlit, Django, Postgres defined as pydantic objects
- **Infrastructure** components (docker, AWS) also defined as pydantic objects

Phidata applications run locally using docker and can be deployed to AWS with 1 command.

## 👩‍💻 How it works

- Create your codebase using a template: `phi ws create`
- Run your app locally: `phi ws up dev:docker`
- Run your app on AWS: `phi ws up prd:aws`

## 🚀 Get Started

- Read the <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">docs</a> for more information.
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a> for help.

## 📖 Quickstart: Build a RAG LLM App

Let's build a **RAG LLM App** using:

- GPT-4 as the LLM
- Streamlit as the chat interface
- FastApi as the backend
- PgVector for knowledge base and storage
- Read the full tutorial <a href="https://docs.phidata.com/quickstart" target="_blank" rel="noopener noreferrer">here</a>.

> Install <a href="https://docs.docker.com/desktop/install/mac-install/" target="_blank" rel="noopener noreferrer">docker desktop</a> to run this app locally.

### Create a virtual environment

Open the `Terminal` and create an `ai` directory with a python virtual environment.

```shell
mkdir ai && cd ai

python3 -m venv aienv
source aienv/bin/activate
```

### Install

Install phidata

```shell
pip install -U phidata
```

### Create your codebase

Create your codebase using the `llm-app` template pre-configured with FastApi, Streamlit and PgVector.

```shell
phi ws create -t llm-app -n llm-app
```

This will create a folder `llm-app` with a pre-built LLM App that you can customize and make your own.

### Serve your LLM App using Streamlit

<a href="https://streamlit.io" target="_blank" rel="noopener noreferrer">Streamlit</a> allows us to build micro front-ends for our LLM App and is extremely useful for building basic applications in pure python. Start the `app` group using:

```shell
phi ws up --group app
```

**Press Enter** to confirm and give a few minutes for the image to download.

### Chat with PDFs

- Open <a href="http://localhost:8501" target="_blank" rel="noopener noreferrer">localhost:8501</a> to view streamlit apps that you can customize and make your own.
- Click on **Chat with PDFs** in the sidebar
- Enter a username and wait for the knowledge base to load.
- Choose the `RAG` Conversation type.
- Ask "How do I make chicken curry?"
- Upload PDFs and ask questions

<img width="800" alt="chat-with-pdf" src="https://github.com/phidatahq/phidata/assets/22579644/a8eff0ac-963c-43cb-a784-920bd6713a48">

### Serve your LLM App using FastApi

Streamlit is great for building micro front-ends but any production application will be built using a front-end framework like `next.js` backed by a RestApi built using a framework like `FastApi`.

Your LLM App comes ready-to-use with FastApi endpoints, start the `api` group using:

```shell
phi ws up --group api
```

**Press Enter** to confirm and give a few minutes for the image to download.

### View API Endpoints

- Open <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">localhost:8000/docs</a> to view the API Endpoints.
- Load the knowledge base using `/v1/pdf/conversation/load-knowledge-base`
- Test the `v1/pdf/conversation/chat` endpoint with `{"message": "How do I make chicken curry?"}`
- The LLM Api comes pre-built with endpoints that you can integrate with your front-end.

### Optional: Run Jupyterlab

A jupyter notebook is a must-have for AI development and your `llm-app` comes with a notebook pre-installed with the required dependencies. Enable it by updating the `workspace/settings.py` file:

```python {{ title: 'workspace/settings.py'}}
...
ws_settings = WorkspaceSettings(
    ...
    # Uncomment the following line
    dev_jupyter_enabled=True,
...
```

Start `jupyter` using:


```shell
phi ws up --group jupyter
```

**Press Enter** to confirm and give a few minutes for the image to download (only the first time). Verify container status and view logs on the docker dashboard.

### View Jupyterlab UI

- Open <a href="http://localhost:8888" target="_blank" rel="noopener noreferrer">localhost:8888</a> to view the Jupyterlab UI. Password: **admin**
- Play around with cookbooks in the `notebooks` folder.

### Delete local resources

Play around and stop the workspace using:

```shell
phi ws down
```

### Run your LLM App on AWS

Read how to <a href="https://docs.phidata.com/quickstart/run-aws" target="_blank" rel="noopener noreferrer">run your LLM App on AWS</a>.

## 📚 More Information:

- Read the <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">docs</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a>
- Email us at <a href="mailto:help@phidata.com" target="_blank" rel="noopener noreferrer">help@phidata.com</a>
