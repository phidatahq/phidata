<h1 align="center">
  phidata
</h1>
<h3 align="center">
  Full Stack AI Toolkit
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

## 🎯 Goal: Provide a paved path to production-ready AI

Phidata is a toolkit for building AI powered software. It enables you to build:
- **RAG Apps**: Connect LLMs to your knowledge base and build context-aware applications.
- **Autonomous Apps**: Give LLMs the ability to call functions and build autonomous applications.
- **Multi-Modal Apps**: Build apps that can process text, images, audio and video.
- **Workflow Specific AI**: Build AI for workflows like data engineering, customer support, sales, marketing, etc.

It achieves this by providing:
- Building blocks: `Conversations`, `Tools`, `Agents`, `KnowledgeBase`, `Storage`
- Tools for serving AI Apps: `FastApi`, `Django`, `Streamlit`, `PgVector`
- Infrastructure for running AI Apps: `Docker`, `AWS`

To simplify development further, phidata provides pre-built templates for common use-cases that you can clone and run with 1 command.  ⭐️ for when you need to spin up an AI project quickly.

## ✨ Motivation

Most AI Apps are built as a house of cards because engineers have to build the Software, Application and Infrastructure layer separately and then glue them together.
This leads to brittle systems that are hard to maintain and productionize.

Phidata bridges the 3 layers of software development and provides a paved path to production-ready AI.

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

## 💻 Quickstart

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
pip install phidata
```

### Create a conversation

Conversations are a human-like interface to language models and the starting point for every AI App.
We send the LLM a message and get a model-generated output as a response.

Conversations come with built-in Memory, Knowledge, Storage and access to Tools.
Giving LLMs the ability to have long-term, knowledge-based Conversations is the first step in our journey to AGI.

- Copy the following code to a file `conversation.py`

```python
from phi.conversation import Conversation

conversation = Conversation()
conversation.print_response('Share a quick healthy breakfast recipe.')
```

- Install openai

```shell
pip install openai
```

- Run your conversation

```shell
python conversation.py
```

### Get structured output from LLM

- Update the `conversation.py` file to:

```python
from pydantic import BaseModel, Field
from phi.conversation import Conversation
from rich.pretty import pprint

class Recipe(BaseModel):
    title: str = Field(..., description='Title of the recipe.')
    ingredients: str = Field(..., description='Ingredients for the recipe.')
    instructions: str = Field(..., description='Instructions for the recipe.')

conversation = Conversation(output_model=Recipe)
breakfast_recipe = conversation.run('Quick healthy breakfast recipe.')
pprint(breakfast_recipe)
```

- Run your conversation again:

```shell
python conversation.py

Recipe(
│   title='Banana and Almond Butter Toast',
│   ingredients='2 slices of whole-grain bread, 1 ripe banana, 2 tablespoons almond butter, 1 teaspoon chia seeds, 1 teaspoon honey (optional)',
│   instructions='Toast the bread slices to desired crispness. Spread 1 tablespoon of almond butter on each slice of toast. Slice the banana and arrange the slices on top of the almond butter. Sprinkle chia seeds over the banana slices. Drizzle honey on top if preferred. Serve immediately.'
)
```

## 🤖 Full Example: Build a RAG LLM App

Let's build a **RAG LLM App** with GPT-4. We'll use:
- PgVector for Knowledge Base and Storage
- Streamlit for the front-end
- FastApi for the back-end
- Read the full tutorial <a href="https://docs.phidata.com/examples/rag-llm-app" target="_blank" rel="noopener noreferrer">here</a>.

> Install <a href="https://docs.docker.com/desktop/install/mac-install/" target="_blank" rel="noopener noreferrer">docker desktop</a> to run this app locally.

### Create your codebase

Create your codebase using the `llm-app` template pre-configured with FastApi, Streamlit and PgVector.

```shell
phi ws create -t llm-app -n llm-app
```

This will create a folder named `llm-app` in the current directory.

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

Read how to <a href="https://docs.phidata.com/guides/llm-app#run-on-aws" target="_blank" rel="noopener noreferrer">run your LLM App on AWS here</a>.

## 📚 More Information:

- Read the <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">documentation</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">Discord</a>
- Email us at <a href="mailto:help@phidata.com" target="_blank" rel="noopener noreferrer">help@phidata.com</a>
