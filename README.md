<h1 align="center">
  phidata
</h1>
<p align="center">
    <em>AI Toolkit for Engineers</em>
</p>

<p align="center">
<a href="https://python.org/pypi/phidata" target="_blank">
    <img src="https://img.shields.io/pypi/v/phidata?color=blue&label=version" alt="version">
</a>
<a href="https://github.com/phidatahq/phidata" target="_blank">
    <img src="https://img.shields.io/badge/python->=3.7-blue" alt="pythonversion">
</a>
<a href="https://github.com/phidatahq/phidata" target="_blank">
    <img src="https://pepy.tech/badge/phidata" alt="downloads">
</a>
<a href="https://github.com/phidatahq/phidata/actions/workflows/build.yml" target="_blank">
    <img src="https://github.com/phidatahq/phidata/actions/workflows/build.yml/badge.svg" alt="build-status">
</a>
</p>

<h2 align="center">
  Build LLM applications using production ready templates
</h2>

<br />

Phidata is an everything-included AI toolkit. It provides pre-built templates for LLM apps.

## 🚀 How it works

- Create your LLM app: `phi ws create`
- Run your app locally: `phi ws up dev:docker`
- Run your app on AWS: `phi ws up prd:aws`

For example, run a RAG Chatbot built with FastApi, Streamlit and PgVector in 2 commands:

```bash
phi ws create -t llm-app -n llm-app  # create the llm-app codebase
phi ws up                            # run the llm-app locally
```

It solves the problem of building LLM powered products by providing:

### 💻 Software layer

- Access to **LLMs** using a human-like `Conversation` interface.
- Components for **building** LLM apps: **RAG, Agents, Workflows**
- Components for **extending** LLM apps: **Knowledge Base, Storage, Memory, Cache**
- Components for **monitoring** LLM apps: **Model Inputs/Outputs, Quality, Cost**
- Components for **improving** LLM apps: **Fine-tuning, RLHF**

### 📱 Application layer

- Tools for running LLM apps: **FastApi, Django, Streamlit**
- Tools for running LLM components: **PgVector, Postgres, Redis**

### 🌉 Infrastructure layer

- Infrastructure for running LLM apps locally: **Docker**
- Infrastructure for running LLM apps in production: **AWS**
- Best practices like testing, formatting, CI/CD, security and secret management.

Phidata bridges the 3 layers of software development to deliver production-grade LLM Apps that you can run with 1 command.

## 🎯 For more information:

- Read the <a href="https://docs.phidata.com" target="_blank">documentation</a>
- Read about <a href="https://docs.phidata.com/intro/basics" target="_blank">phidata basics</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank">Discord</a>
- Email us at <a href="mailto:help@phidata.com" target="_blank">help@phidata.com</a>

## 👩‍💻 Example: Build a RAG LLM App 🧑‍💻

Let's build a **RAG LLM App** with GPT-4. We'll use PgVector for Knowledge Base and Storage and serve the app using Streamlit and FastApi.

> Install <a href="https://docs.docker.com/desktop/install/mac-install/" target="_blank">docker desktop</a> to run the app locally.

> Read the full tutorial <a href="https://docs.phidata.com/how-to/rag-llm-app" target="_blank">here</a>

### Setup

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

Create your codebase using the `llm-app` template that is pre-configured with FastApi, Streamlit and PgVector. Use this codebase as a starting point for your LLM product.

```bash
phi ws create -t llm-app -n llm-app
```

This will create a folder named `llm-app`

<img src="https://github.com/phidatahq/phidata/assets/22579644/dee7b884-028e-48a0-9074-4deb7a055b97" height=600  alt="create-llm-app"/>

### Serve your LLM App using Streamlit

<a href="https://streamlit.io" target="_blank">Streamlit</a> allows us to build micro front-ends for our LLM App and is extremely useful for building basic applications in pure python. Start the `app` group using:

```bash
phi ws up --group app
```

<img src="https://github.com/phidatahq/phidata/assets/22579644/dee35e20-9fe5-4623-af5e-2e8a6ffac58c" height=600  alt="run-llm-app"/>

**Press Enter** to confirm and give a few minutes for the image to download (only the first time). Verify container status and view logs on the docker dashboard.

Open <a href="http://localhost:8501" target="_blank">localhost:8501</a> to view streamlit apps that you can customize and make your own.

### Chat with PDFs

- Click on **Chat with PDFs** in the sidebar
- Enter a username and wait for the knowledge base to load.
- Choose the `RAG` Conversation type.
- Ask "How do I make chicken curry?"

<img width="1573" alt="chat-with-pdf" src="https://github.com/phidatahq/phidata/assets/22579644/8529aad8-f74c-464d-8bf8-2272a3281b25">

### Serve your LLM App using FastApi

Streamlit is great for building micro front-ends but any production application will be built using a front-end framework like `next.js` backed by a RestApi built with a framework like `FastApi`.

Your LLM App comes pre-configured with FastApi, start the `api` group using:

```bash
phi ws up --group api
```

**Press Enter** to confirm and give a few minutes for the image to download.

### View API Endpoints

- Open <a href="http://localhost:8000/docs" target="_blank">localhost:8000/docs</a> to view the API Endpoints.
- Load the knowledge base using `/v1/pdf/conversation/load-knowledge-base`
- Test the `v1/pdf/conversation/chat` endpoint with `{"message": "How do I make chicken curry?"}`
- The LLM Api comes pre-build with the endpoints you need to integrate with your front-end.

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

- Open <a href="http://localhost:8888" target="_blank">localhost:8888</a> to view the Jupyterlab UI. Password: **admin**
- Open `notebooks/chatgpt_stream` to test the ChatGPT Api.

### Read Local PDFs

To read local PDFs, update the `llm/knowledge_base.py` file to use the `PDFKnowledgeBase`

```python
...
pdf_knowledge_base = PDFKnowledgeBase(
    path="data/pdfs",
    # Table name: llm.pdf_documents
    vector_db=PgVector(
        collection="pdf_documents",
        db_url=db_url,
        schema="llm",
    ),
    reader=PDFReader(chunk=False),
)
...
```

### Delete local resources

Play around and stop the workspace using:

```bash
phi ws down
```

### Run your LLM App on AWS

Read how to <a href="https://docs.phidata.com/guides/llm-app#run-on-aws" target="_blank">run your LLM App on AWS here</a>.

### More information:

- Read the <a href="https://docs.phidata.com" target="_blank">documentation</a>
- Read about <a href="https://docs.phidata.com/intro/basics" target="_blank">phidata basics</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank">Discord</a>
- Email us at <a href="mailto:help@phidata.com" target="_blank">help@phidata.com</a>
