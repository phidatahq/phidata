<h1 align="center">
  phidata
</h1>
<h3 align="center">
  Build human-like AI products
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

Toolkit for building AI products using a human-like `Conversation` interface.
Like we have conversations with human specialists, now we can have conversations with AI specialists.

**Conversations** come with built-in **memory**, **knowledge**, **storage**, **tools** and can be used to build pretty much any kind of **RAG**, **Autonomous** or **Multimodal** application. For example:

- **PDF Assistants:** Upload PDFs and ask questions.
- **Python Engineers:** Perform tasks by writing and running python scripts.
- **Data Analysts:** Analyze data by writing and running SQL queries.
- **Stock Analysts:** Analyze stocks and research companies.
- **Marketing Analysts:** Provide marketing insights, copywriting and content ideas.

## 👩‍💻 Getting Started

<details>

<summary><h3>Installation</h3></summary>

- Open the `Terminal` and create an `ai` directory with a python virtual environment.

```shell
mkdir ai && cd ai

python3 -m venv aienv
source aienv/bin/activate
```

- Install phidata

```shell
pip install -U phidata
```

</details>

<details>

<summary><h3>Create a Conversation</h3></summary>

**Conversations** are a human-like interface to language models and the starting point for every AI App.
Conversations come with built-in **memory**, **knowledge**, **storage** and access to **tools**.

- Create a file `conversation.py` and install openai using `pip install openai`

```python
from phi.conversation import Conversation

conversation = Conversation()
conversation.print_response('Share a quick healthy breakfast recipe.')
```

- Run the `conversation.py` file

```shell
python conversation.py
```

- See a simple conversation in action

```shell
╭──────────┬────────────────────────────────────────────────────────╮
│ Message  │ Share a quick healthy breakfast recipe.                │
├──────────┼────────────────────────────────────────────────────────┤
│ Response │ Absolutely! Here's a quick and healthy breakfast       │
│ (2.1s)   │ recipe for a yogurt parfait:                           │
│          │                                                        │
│          │                 Healthy Yogurt Parfait                 │
│          │                                                        │
│          │                      Ingredients:                      │
│          │                                                        │
│          │  • Greek yogurt                                        │
│          │  • Fresh berries (e.g., strawberries, blueberries,     │
│          │    raspberries)                                        │
│          │  • Granola                                             │
│          │  • Honey or maple syrup (optional)                     │
│          │  • Chia seeds (optional)                               │
│          │                                                        │
│          │                     Instructions:                      │
│          │                                                        │
│          │  1 In a clear glass or bowl, layer Greek yogurt, fresh │
│          │    berries, and granola.                               │
│          │  2 Repeat the layers until the glass is filled.        │
│          │  3 Drizzle with honey or maple syrup for sweetness, if │
│          │    desired.                                            │
│          │  4 Optional: Sprinkle with chia seeds for added        │
│          │    nutritional benefits.                               │
│          │                                                        │
│          │ Enjoy your nutritious and delicious yogurt parfait!    │
╰──────────┴────────────────────────────────────────────────────────╯
```

</details>

<details>

<summary><h3>Create a Python Engineer</h3></summary>

You can have a Conversation with an `Agent` that is designed for a specific task. For example: `PythonAgent` can perform virtually any task using python code.

- Create a file `python_agent.py` and install pandas using `pip install pandas`

```python
from phi.agent.python import PythonAgent
from phi.file.local.csv import CsvFile

python_agent = PythonAgent(
    files=[
        CsvFile(
            path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
            description="Contains information about movies from IMDB.",
        )
    ],
    pip_install=True,
    show_function_calls=True,
)

python_agent.print_response("What is the average rating of movies?")
```

- Run the `python_agent.py` file

```shell
python python_agent.py
```

- See it work through the problem

```shell
WARNING  PythonTools can run arbitrary code, please provide human supervision.
INFO     Saved: .../average_rating.py
INFO     Running .../average_rating.py
╭──────────┬────────────────────────────────────────────────────────╮
│ Message  │ What is the average rating of movies?                  │
├──────────┼────────────────────────────────────────────────────────┤
│ Response │                                                        │
│ (4.1s)   │  • Running:                                            │
│          │    save_to_file_and_run(file_name=average_rating,      │
│          │    code=..., variable_to_return=average_rating)        │
│          │                                                        │
│          │ The average rating of the movies is approximately      │
│          │ 6.72.                                                  │
╰──────────┴────────────────────────────────────────────────────────╯
```

</details>

<details>

<summary><h3>Create a Data Analyst</h3></summary>

Use the `DuckDbAgent` to perform data analysis using SQL queries.

- Create a file `data_analyst.py` and install duckdb using `pip install duckdb`

```python
import json
from phi.agent.duckdb import DuckDbAgent

duckdb_agent = DuckDbAgent(
    semantic_model=json.dumps({
        "tables": [
            {
                "name": "movies",
                "description": "Contains information about movies from IMDB.",
                "path": "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
            }
        ]
    }),
)

duckdb_agent.print_response("What is the average rating of movies? Show me the SQL.")
```

- Run the `data_analyst.py` file

```shell
python data_analyst.py
```

- See it work through the problem

```shell
INFO     Running: SHOW TABLES
INFO     Running: CREATE TABLE IF NOT EXISTS 'movies'
         AS SELECT * FROM
         'https://phidata-public.s3.amazonaws.com/demo_
         data/IMDB-Movie-Data.csv'
INFO     Running: DESCRIBE movies
INFO     Running: SELECT AVG(Rating) AS average_rating
         FROM movies
╭──────────┬────────────────────────────────────────────────────────╮
│ Message  │ What is the average rating of movies? Show me the SQL. │
├──────────┼────────────────────────────────────────────────────────┤
│ Response │ The average rating of movies in the dataset is 6.72.   │
│ (7.6s)   │                                                        │
│          │ Here is the SQL query used to calculate the average    │
│          │ rating:                                                │
│          │                                                        │
│          │                                                        │
│          │  SELECT AVG(Rating) AS average_rating                  │
│          │  FROM movies;                                          │
│          │                                                        │
╰──────────┴────────────────────────────────────────────────────────╯
```

</details>

<details>

<summary><h3>Return a Pydantic Model as output</h3></summary>

One of our favorite features is generating structured data from sparse information.

Meaning we can use LLMs to fill in pydantic models and generate content which previously could not be possible.
In this example, we generate an object of the `MovieScript` class.

- Create a file `movie_generator.py`

```python
from typing import List
from pydantic import BaseModel, Field
from phi.conversation import Conversation
from rich.pretty import pprint


class MovieScript(BaseModel):
    setting: str = Field(..., description="Setting of the movie. If not available, provide a random setting.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(
        ..., description="Genre of the movie. If not available, select action, thriller or romantic comedy."
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="2 sentence story of the movie.")


movie_generator = Conversation(
    system_prompt="Generate a movie",
    output_model=MovieScript,
)

pprint(movie_generator.run("New York"))
```

- Run the `movie_generator.py` file

```shell
python movie_generator.py
```

- See how the conversation generates a structured output

```shell
MovieScript(
│   setting='New York',
│   ending='happy ending',
│   genre='romantic comedy',
│   name='Love in the City',
│   characters=['Emma', 'Jack', 'Olivia', 'Michael'],
│   storyline="In the bustling streets of New York, Emma, an ambitious young woman, meets Jack, a charming but jobless artist. As they navigate the city's challenges, their bond grows stronger, leading to unexpected romance and heartwarming adventures."
)
```

</details>

## 🚀 Examples

<details>

<summary><h3>Create a PDF Assistant with Knowledge & Storage</h3></summary>

- **Knowledge Base:** a database of information that the AI can search to improve its responses.
- **Storage:** provides long term memory for `Conversations`.

Let's run `PgVector` as it can provide both, knowledge and storage for our Conversations.

- Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) for running PgVector in a container.
- Create a file `resources.py` with the following contents

```python
from phi.docker.app.postgres import PgVectorDb
from phi.docker.resources import DockerResources

# -*- PgVector running on port 5432:5432
vector_db = PgVectorDb(
    pg_user="llm",
    pg_password="llm",
    pg_database="llm",
    debug_mode=True,
)

# -*- DockerResources
dev_docker_resources = DockerResources(apps=[vector_db])
```

- Start `PgVector` using

```shell
phi start resources.py
```

- Create a file `pdf_assistant.py` and install libraries using `pip install pgvector pypdf psycopg sqlalchemy`

```python
import typer
from rich.prompt import Prompt
from typing import Optional, List

from phi.conversation import Conversation
from phi.storage.conversation.postgres import PgConversationStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector

from resources import vector_db

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://www.family-action.org.uk/content/uploads/2019/07/meals-more-recipes.pdf"],
    vector_db=PgVector(
        collection="recipes",
        db_url=vector_db.get_db_connection_local(),
    ),
)

storage = PgConversationStorage(
    table_name="recipe_conversations",
    db_url=vector_db.get_db_connection_local(),
)


def llm_app(new: bool = False, user: str = "user"):
    conversation_id: Optional[str] = None

    if not new:
        existing_conversation_ids: List[str] = storage.get_all_conversation_ids(user)
        if len(existing_conversation_ids) > 0:
            conversation_id = existing_conversation_ids[0]

    conversation = Conversation(
        user_name=user,
        id=conversation_id,
        knowledge_base=knowledge_base,
        storage=storage,
        # Uncomment the following line to use traditional RAG
        # add_references_to_prompt=True,
        function_calls=True,
        show_function_calls=True,
    )
    if conversation_id is None:
        conversation_id = conversation.id
        print(f"Started Conversation: {conversation_id}\n")
    else:
        print(f"Continuing Conversation: {conversation_id}\n")

    conversation.knowledge_base.load(recreate=False)
    while True:
        message = Prompt.ask(f"[bold] :sunglasses: {user} [/bold]")
        if message in ("exit", "bye"):
            break
        conversation.print_response(message)


if __name__ == "__main__":
    typer.run(llm_app)
```

- Run the `pdf_assistant.py` file

```shell
python pdf_assistant.py
```

- Ask a question:

```
How do I make chicken tikka salad?
```

- Message `bye` to exit, start the app again and ask:

```
What was my last message?
```

See how the app maintains has storage across sessions.

- Run the `pdf_assistant.py` file with the `--new` flag to start a new conversation.

```shell
python pdf_assistant.py --new
```

- Stop PgVector

Play around and then stop `PgVector` using `phi stop resources.py`

```shell
phi stop resources.py
```

</details>

<details>

<summary><h3>Build an LLM App using Streamlit, FastApi and PgVector</h3></summary>

Templates are **pre-built AI Apps** that can be used as a starting point for your own AI. The general workflow is:

- Create your codebase using a template: `phi ws create`
- Run your app locally: `phi ws up dev:docker`
- Run your app on AWS: `phi ws up prd:aws`

Let's build an **LLM App** using GPT-4 as the LLM, Streamlit as the chat interface, FastApi as the backend and PgVector for knowledge and storage.

> Read the full tutorial <a href="https://docs.phidata.com/quickstart" target="_blank" rel="noopener noreferrer">here</a>.

- Create your codebase

Create your codebase using the `llm-app` template pre-configured with FastApi, Streamlit and PgVector.

```shell
phi ws create -t llm-app -n llm-app
```

This will create a folder `llm-app` with a pre-built LLM App that you can customize and make your own.

- Serve your LLM App using Streamlit

<a href="https://streamlit.io" target="_blank" rel="noopener noreferrer">Streamlit</a> allows us to build micro front-ends for our LLM App and is extremely useful for building basic applications in pure python. Start the `app` group using:

```shell
phi ws up --group app
```

**Press Enter** to confirm and give a few minutes for the image to download.

- Chat with PDFs

- Open <a href="http://localhost:8501" target="_blank" rel="noopener noreferrer">localhost:8501</a> to view streamlit apps that you can customize and make your own.
- Click on **Chat with PDFs** in the sidebar
- Enter a username and wait for the knowledge base to load.
- Choose the `RAG` or `Autonomous` Conversation type.
- Ask "How do I make chicken curry?"
- Upload PDFs and ask questions

<img width="800" alt="chat-with-pdf" src="https://github.com/phidatahq/phidata/assets/22579644/a8eff0ac-963c-43cb-a784-920bd6713a48">

- Serve your LLM App using FastApi

Streamlit is great for building micro front-ends but any production application will be built using a front-end framework like `next.js` backed by a RestApi built using a framework like `FastApi`.

Your LLM App comes ready-to-use with FastApi endpoints, start the `api` group using:

```shell
phi ws up --group api
```

**Press Enter** to confirm and give a few minutes for the image to download.

- View API Endpoints

- Open <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">localhost:8000/docs</a> to view the API Endpoints.
- Load the knowledge base using `/v1/pdf/conversation/load-knowledge-base`
- Test the `v1/pdf/conversation/chat` endpoint with `{"message": "How do I make chicken curry?"}`
- The LLM Api comes pre-built with endpoints that you can integrate with your front-end.

- Optional: Run Jupyterlab

A jupyter notebook is a must-have for AI development and your `llm-app` comes with a notebook pre-installed with the required dependencies. Enable it by updating the `workspace/settings.py` file:

```python
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

- View Jupyterlab UI

- Open <a href="http://localhost:8888" target="_blank" rel="noopener noreferrer">localhost:8888</a> to view the Jupyterlab UI. Password: **admin**
- Play around with cookbooks in the `notebooks` folder.

- Delete local resources

Play around and stop the workspace using:

```shell
phi ws down
```

- Run your LLM App on AWS

Read how to <a href="https://docs.phidata.com/quickstart/run-aws" target="_blank" rel="noopener noreferrer">run your LLM App on AWS</a>.

</details>

## 📚 More Information:

- Read the <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">docs</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a>
- Email us at <a href="mailto:help@phidata.com" target="_blank" rel="noopener noreferrer">help@phidata.com</a>
