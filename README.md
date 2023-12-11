<h1 align="center">
  phidata
</h1>
<h3 align="center">
  AI Toolkit for Engineers 🚀
</h3>
<p align="center">
  ⭐️ for when you need to spin up an AI project quickly.
</p>
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

Phidata is a toolkit for building production-grade AI Applications. It provides:
- Pre-built templates with best practices.
- Classes for building your application: `Conversations`, `Agents`, `KnowledgeBase`, `Storage`
- Tools for serving your application: `FastApi`, `Django`, `Streamlit`, `PgVector`
- Infrastructure for running your application: `Docker`, `AWS`

## 🎯 Motivation

Most AI Apps are built as a house of cards because engineers have to build
the Software, Application and Infrastructure layer manually. Phidata bridges the 3 layers of software development
to deliver production-grade AI Apps that you can run with 1 command.

## 🚀 How it works

- Create your codebase using a template: `phi ws create`
- Run your app locally: `phi ws up dev:docker`
- Run your app on AWS: `phi ws up prd:aws`

## ⭐ Features:
- **Powerful:** Get a production-ready AI App with 1 command.
- **Simple**: Built using a human-like `Conversation` interface to language models.
- **Production Ready:** Your app can be deployed to aws with 1 command.

## 📚 More Information:

- Read the <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">documentation</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">Discord</a>
- Email us at <a href="mailto:help@phidata.com" target="_blank" rel="noopener noreferrer">help@phidata.com</a>

## 💻 Example: Build a RAG LLM App

Let's build a **RAG LLM App** with GPT-4. We'll use PgVector for Knowledge Base and Storage and serve the app using Streamlit and FastApi. Read the full tutorial <a href="https://docs.phidata.com/examples/rag-llm-app" target="_blank" rel="noopener noreferrer">here</a>.

> Install <a href="https://docs.docker.com/desktop/install/mac-install/" target="_blank" rel="noopener noreferrer">docker desktop</a> to run this app locally.

### Installation

Open the `Terminal` and create an `ai` directory with a python virtual environment.

```bash
mkdir ai && cd ai

python3 -m venv aienv
source aienv/bin/activate
```

Install phidata

```bash
pip install phidata
```

### Create your codebase

Create your codebase using the `llm-app` template pre-configured with FastApi, Streamlit and PgVector. Use this codebase as a starting point for your LLM product.

```bash
phi ws create -t llm-app -n llm-app
```

This will create a folder named `llm-app`

### Serve your LLM App using Streamlit

<a href="https://streamlit.io" target="_blank" rel="noopener noreferrer">Streamlit</a> allows us to build micro front-ends for our LLM App and is extremely useful for building basic applications in pure python. Start the `app` group using:

```bash
phi ws up --group app
```

**Press Enter** to confirm and give a few minutes for the image to download (only the first time). Verify container status and view logs on the docker dashboard.

### Example: Chat with PDFs

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

```bash
phi ws up --group api
```

**Press Enter** to confirm and give a few minutes for the image to download.

### View API Endpoints

- Open <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">localhost:8000/docs</a> to view the API Endpoints.
- Load the knowledge base using `/v1/pdf/conversation/load-knowledge-base`
- Test the `v1/pdf/conversation/chat` endpoint with `{"message": "How do I make chicken curry?"}`
- The LLM Api comes pre-built with endpoints that you can integrate with your front-end.

### Optional: Run Jupyterlab

A jupyter notebook is a must have for AI development and your `llm-app` comes with a notebook pre-installed with the required dependencies. Enable it by updating the `workspace/settings.py` file:

```python {{ title: 'workspace/settings.py'}}
...
ws_settings = WorkspaceSettings(
    ...
    # Uncomment the following line
    dev_jupyter_enabled=True,
...
```

Start `jupyter` using:


```bash
phi ws up --group jupyter
```

**Press Enter** to confirm and give a few minutes for the image to download (only the first time). Verify container status and view logs on the docker dashboard.

### View Jupyterlab UI

- Open <a href="http://localhost:8888" target="_blank" rel="noopener noreferrer">localhost:8888</a> to view the Jupyterlab UI. Password: **admin**
- Play around with cookbooks in the `notebooks` folder.

### Delete local resources

Play around and stop the workspace using:

```bash
phi ws down
```

### Run your LLM App on AWS

Read how to <a href="https://docs.phidata.com/guides/llm-app#run-on-aws" target="_blank" rel="noopener noreferrer">run your LLM App on AWS here</a>.

## 📚 More Information:

- Read the <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">documentation</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">Discord</a>
- Email us at <a href="mailto:help@phidata.com" target="_blank" rel="noopener noreferrer">help@phidata.com</a>
