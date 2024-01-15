<h1 align="center">
  phidata
</h1>
<h3 align="center">
  Build AI Assistants using language models
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

A toolkit for building AI Assistants using LLM function calling.

Assistants can achieve any task by intelligently choosing their course of action by [function calling](https://platform.openai.com/docs/guides/function-calling).

They come with built-in **memory**, **knowledge**, **storage** and **tools**, making it easy to build any kind of RAG, Autonomous or Multimodal application. For example:

- **PDF Assistants:** Answer questions using PDFs.
- **Data Assistants:** Analyze data by running SQL queries.
- **Python Assistants:** Perform tasks by running python code.
- **Stock Assistants:** Analyze stocks and research companies.
- **Marketing Assistants:** Provide marketing insights, copywriting and content ideas.
- **Sales Assistants:** Answer customer queries using product descriptions and purchase history.
- **Customer Support Assistants:** Answer customer queries using user manuals.
- **Real Estate Assistants:** Help search property listings using neighborhood information and user preferences.
- **Travel Assistants:** Help plan travel by researching destinations and booking tickets.
- **Meal Prep Assistants:** Help plan meals by researching recipes and adding ingredients to shopping lists.

After building an Assistant, serve it using **Streamlit**, **FastApi** or **Django** to build an AI App.

## 👩‍💻 Getting Started

### Installation

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

<details>

<summary><h3>Create an Assistant</h3></summary>

**Assistants** provide a human-like interface to language models and come with built-in **memory**, **knowledge**, **storage** and **tools**.

- Create a file `assistant.py` and install openai using `pip install openai`

```python
from phi.assistant import Assistant

assistant = Assistant(description="You help people with their health and fitness goals.")
assistant.print_response("Share a quick healthy breakfast recipe.")
```

- Run the `assistant.py` file

```shell
python assistant.py
```

- See a simple assistant in action

```shell
╭──────────┬───────────────────────────────────────────────────────────────────╮
│ Message  │ Share a quick healthy breakfast recipe.                           │
├──────────┼───────────────────────────────────────────────────────────────────┤
│ Response │ Sure! Here's a quick and healthy breakfast recipe for you:        │
│ (3.3s)   │                                                                   │
│          │ Greek Yogurt Parfait:                                             │
│          │                                                                   │
│          │ Ingredients:                                                      │
│          │                                                                   │
│          │  • 1 cup Greek yogurt                                             │
│          │  • 1/2 cup fresh mixed berries (strawberries, blueberries,        │
│          │    raspberries)                                                   │
│          │  • 1/4 cup granola                                                │
│          │  • 1 tablespoon honey                                             │
│          │  • Optional: chia seeds or sliced almonds for extra nutrients     │
│          │                                                                   │
│          │ Instructions:                                                     │
│          │                                                                   │
│          │  1 In a glass or bowl, layer Greek yogurt, mixed berries, and     │
│          │    granola.                                                       │
│          │  2 Drizzle honey on top for some natural sweetness.               │
│          │  3 Optional: Sprinkle with chia seeds or sliced almonds for added │
│          │    texture and nutrients.                                         │
│          │                                                                   │
│          │ Enjoy your nutritious and delicious Greek yogurt parfait!         │
╰──────────┴───────────────────────────────────────────────────────────────────╯
```

</details>

<details>

<summary><h3>Create a Python Assistant</h3></summary>

The `PythonAssistant` can perform virtually any task using python code.

- Create a file `python_assistant.py` and install pandas using `pip install pandas`

```python
from phi.assistant.python import PythonAssistant
from phi.file.local.csv import CsvFile

python_assistant = PythonAssistant(
    files=[
        CsvFile(
            path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
            description="Contains information about movies from IMDB.",
        )
    ],
    pip_install=True,
    show_tool_calls=True,
)

python_assistant.print_response("What is the average rating of movies?")
```

- Run the `python_assistant.py` file

```shell
python python_assistant.py
```

- See it work through the problem

```shell
WARNING  PythonTools can run arbitrary code, please provide human supervision.
INFO     Saved: /Users/zu/ai/average_rating
INFO     Running /Users/zu/ai/average_rating
╭──────────┬───────────────────────────────────────────────────────────────────╮
│ Message  │ What is the average rating of movies?                             │
├──────────┼───────────────────────────────────────────────────────────────────┤
│ Response │                                                                   │
│ (4.1s)   │  • Running: save_to_file_and_run(file_name=average_rating,        │
│          │    code=..., variable_to_return=average_rating)                   │
│          │                                                                   │
│          │ The average rating of movies is approximately 6.72.               │
╰──────────┴───────────────────────────────────────────────────────────────────╯
```

</details>

<details>

<summary><h3>Create a Data Assistant</h3></summary>

The `DuckDbAssistant` can perform data analysis using SQL queries.

- Create a file `data_assistant.py` and install duckdb using `pip install duckdb`

```python
import json
from phi.assistant.duckdb import DuckDbAssistant

duckdb_assistant = DuckDbAssistant(
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

duckdb_assistant.print_response("What is the average rating of movies? Show me the SQL.")
```

- Run the `data_assistant.py` file

```shell
python data_assistant.py
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

<summary><h3>Structured output from a Movie Assistant</h3></summary>

One of our favorite features is generating structured data (i.e. a pydantic model) from sparse information.
Meaning we can use LLMs to return pydantic models and generate content which previously could not be possible.
In this example, our movie assistant generates an object of the `MovieScript` class.

- Create a file `movie_assistant.py`

```python
from typing import List
from pydantic import BaseModel, Field
from rich.pretty import pprint
from phi.assistant import Assistant


class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(..., description="Genre of the movie. If not available, select action, thriller or romantic comedy.")
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")


movie_assistant = Assistant(
    description="You help people write movie ideas.",
    output_model=MovieScript,
)

pprint(movie_assistant.run("New York"))
```

- Run the `movie_assistant.py` file

```shell
python movie_assistant.py
```

- See how the assistant generates a structured output

```shell
MovieScript(
│   setting='A bustling and vibrant New York City',
│   ending='The protagonist saves the city and reconciles with their estranged family.',
│   genre='action',
│   name='City Pulse',
│   characters=['Alex Mercer', 'Nina Castillo', 'Detective Mike Johnson'],
│   storyline='In the heart of New York City, a former cop turned vigilante, Alex Mercer, teams up with a street-smart activist, Nina Castillo, to take down a corrupt political figure who threatens to destroy the city. As they navigate through the intricate web of power and deception, they uncover shocking truths that push them to the brink of their abilities. With time running out, they must race against the clock to save New York and confront their own demons.'
)
```

</details>

## 🚀 Examples

<details>

<summary><h3>Create a PDF Assistant with Knowledge & Storage</h3></summary>

- **Knowledge Base:** information that an Assistant can search to improve its responses. Uses a vector db.
- **Storage:** provides long term memory for Assistants. Uses a database.

Let's run `PgVector` as it can provide both, knowledge and storage for our Assistants.

- Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) for running PgVector in a container.
- Create a file `resources.py` with the following contents

```python
from phi.docker.app.postgres import PgVectorDb
from phi.docker.resources import DockerResources

# -*- PgVector running on port 5432:5432
vector_db = PgVectorDb(
    pg_user="ai",
    pg_password="ai",
    pg_database="ai",
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
from phi.assistant import Assistant
from phi.storage.assistant.postgres import PgAssistantStorage
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

storage = PgAssistantStorage(
    table_name="recipe_assistant",
    db_url=vector_db.get_db_connection_local(),
)


def recipe_assistant(new: bool = False, user: str = "user"):
    run_id: Optional[str] = None

    if not new:
        existing_run_ids: List[str] = storage.get_all_run_ids(user)
        if len(existing_run_ids) > 0:
            run_id = existing_run_ids[0]

    assistant = Assistant(
        run_id=run_id,
        user_id=user,
        knowledge_base=knowledge_base,
        storage=storage,
        # tool_calls=True adds functions to
        # search the knowledge base and chat history
        tool_calls=True,
        show_tool_calls=True,
        # Uncomment the following line to use traditional RAG
        # add_references_to_prompt=True,
    )
    if run_id is None:
        run_id = assistant.run_id
        print(f"Started Run: {run_id}\n")
    else:
        print(f"Continuing Run: {run_id}\n")

    assistant.knowledge_base.load(recreate=False)
    while True:
        message = Prompt.ask(f"[bold] :sunglasses: {user} [/bold]")
        if message in ("exit", "bye"):
            break
        assistant.print_response(message)


if __name__ == "__main__":
    typer.run(recipe_assistant)
```

- Run the `pdf_assistant.py` file

```shell
python pdf_assistant.py
```

- Ask a question:

```
How do I make chicken tikka salad?
```

- See how the Assistant searches the knowledge base and returns a response.

<details>

<summary>Result</summary>

```shell
Started Run: d28478ea-75ed-4710-8191-22564ebfb140

INFO     Loading knowledge base
INFO     Reading:
         https://www.family-action.org.uk/content/uploads/2019/07/meals-more-recipes.pdf
INFO     Loaded 82 documents to knowledge base
 😎 user : How do I make chicken tikka salad?
╭──────────┬─────────────────────────────────────────────────────────────────────────────────╮
│ Message  │ How do I make chicken tikka salad?                                              │
├──────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ Response │                                                                                 │
│ (7.2s)   │  • Running: search_knowledge_base(query=chicken tikka salad)                    │
│          │                                                                                 │
│          │ I found a recipe for Chicken Tikka Salad that serves 2. Here are the            │
│          │ ingredients and steps:                                                          │
│          │                                                                                 │
│          │ Ingredients:                                                                    │

...
```

</details>

- Message `bye` to exit, start the app again and ask:

```
What was my last message?
```

See how the assistant now maintains storage across sessions.

- Run the `pdf_assistant.py` file with the `--new` flag to start a new run.

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

<summary><h3>Build an AI App using Streamlit, FastApi and PgVector</h3></summary>

Phidata provides **pre-built templates** for AI Apps that you can use as a starting point. The general workflow is:

- Create your codebase using a template: `phi ws create`
- Run your app locally: `phi ws up dev:docker`
- Run your app on AWS: `phi ws up prd:aws`

Let's build an **AI App** using GPT-4 as the LLM, Streamlit as the chat interface, FastApi as the backend and PgVector for knowledge and storage. Read the full tutorial <a href="https://docs.phidata.com/ai-app/run-local" target="_blank" rel="noopener noreferrer">here</a>.

### Step 1: Create your codebase

Create your codebase using the `ai-app` template

```shell
phi ws create -t ai-app -n ai-app
```

This will create a folder `ai-app` with a pre-built AI App that you can customize and make your own.

### Step 2: Serve your App using Streamlit

<a href="https://streamlit.io" target="_blank" rel="noopener noreferrer">Streamlit</a> allows us to build micro front-ends and is extremely useful for building basic applications in pure python. Start the `app` group using:

```shell
phi ws up --group app
```

**Press Enter** to confirm and give a few minutes for the image to download.

#### PDF Assistant

- Open <a href="http://localhost:8501" target="_blank" rel="noopener noreferrer">localhost:8501</a> to view streamlit apps that you can customize and make your own.
- Click on **PDF Assistant** in the sidebar
- Enter a username and wait for the knowledge base to load.
- Choose either the `RAG` or `Autonomous` Assistant type.
- Ask "How do I make chicken curry?"
- Upload PDFs and ask questions

<img width="800" alt="chat-with-pdf" src="https://github.com/phidatahq/phidata/assets/22579644/a8eff0ac-963c-43cb-a784-920bd6713a48">

### Step 3: Serve your App using FastApi

Streamlit is great for building micro front-ends but any production application will be built using a front-end framework like `next.js` backed by a RestApi built using a framework like `FastApi`.

Your AI App comes ready-to-use with FastApi endpoints, start the `api` group using:

```shell
phi ws up --group api
```

**Press Enter** to confirm and give a few minutes for the image to download.

- View API Endpoints

- Open <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">localhost:8000/docs</a> to view the API Endpoints.
- Load the knowledge base using `/v1/assitants/load-knowledge-base`
- Test the `v1/assitants/chat` endpoint with `{"message": "How do I make chicken curry?"}`
- The Api comes pre-built with endpoints that you can integrate with your front-end.

### Optional: Run Jupyterlab

A jupyter notebook is a must-have for AI development and your `ai-app` comes with a notebook pre-installed with the required dependencies. Enable it by updating the `workspace/settings.py` file:

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

#### View Jupyterlab UI

- Open <a href="http://localhost:8888" target="_blank" rel="noopener noreferrer">localhost:8888</a> to view the Jupyterlab UI. Password: **admin**
- Play around with cookbooks in the `notebooks` folder.

- Delete local resources

### Step 4: Stop the workspace

Play around and stop the workspace using:

```shell
phi ws down
```

### Step 5: Run your AI App on AWS

Read how to <a href="https://docs.phidata.com/quickstart/run-aws" target="_blank" rel="noopener noreferrer">run your AI App on AWS</a>.

</details>

## 📚 Resources

- Read the <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">documentation</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a>
- Email us at <a href="mailto:help@phidata.com" target="_blank" rel="noopener noreferrer">help@phidata.com</a>
