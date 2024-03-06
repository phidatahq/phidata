<h1 align="center">
  phidata
</h1>
<h3 align="center">
  Function calling is all you need
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

## What is phidata?

Phidata is a toolkit for building AI Assistants using function calling.

Function calling enables LLMs to achieve tasks by calling functions and intelligently choosing their next step based on the response, just like how humans solve problems.

![assistants](https://github.com/phidatahq/phidata/assets/22579644/facb618c-17bd-4ab8-99eb-c4c8309e0f45)

## How it works

- **Step 1:** Create an `Assistant`
- **Step 2:** Add Tools (functions), Knowledge (vectordb) and Storage (database)
- **Step 3:** Serve using Streamlit, FastApi or Django to build your AI application

## Installation

```shell
pip install -U phidata
```

## Example 1: Assistant that can search the web

Create a file `assistant.py`

```python
from phi.assistant import Assistant

assistant = Assistant(description="You help people with their health and fitness goals.")
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
```

Install openai and run the `Assistant`

```shell
pip install openai

python assistant.py
```

Add `DuckDuckGo` functions to let the `Assistant` search the web

```python
from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(tools=[DuckDuckGo()], show_tool_calls=True)
assistant.print_response("Whats happening in France?", markdown=True)
```

Install `duckduckgo-search` and run the `Assistant`

```shell
pip install duckduckgo-search

python assistant.py
```

## Example 2: Assistant that can write and run python code

The `PythonAssistant` can achieve tasks using python code. Create a file `python_assistant.py`

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

python_assistant.print_response("What is the average rating of movies?", markdown=True)
```

Install pandas and run the `python_assistant.py`

```shell
pip install pandas

python python_assistant.py
```

## Example 3: Assistant that can analyze data using SQL

The `DuckDbAssistant` can perform data analysis using SQL. Create a file `data_assistant.py`

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

duckdb_assistant.print_response("What is the average rating of movies? Show me the SQL.", markdown=True)
```

Install duckdb and run the `data_assistant.py` file

```shell
pip install duckdb

python data_assistant.py
```

## Demos

Checkout these AI apps showcasing the advantage of function calling:

- <a href="https://pdf.aidev.run/" target="_blank" rel="noopener noreferrer">PDF AI</a> that summarizes and answers questions from PDFs.
- <a href="https://arxiv.aidev.run/" target="_blank" rel="noopener noreferrer">ArXiv AI</a> that answers questions about ArXiv papers using the ArXiv API.
- <a href="https://hn.aidev.run/" target="_blank" rel="noopener noreferrer">HackerNews AI</a> that interacts with the HN API to summarize stories, users, find out what's trending, summarize topics.
- <a href="https://demo.aidev.run/" target="_blank" rel="noopener noreferrer">Demo Streamlit App</a> serving a PDF, Image and Website Assistant (password: admin)
- <a href="https://api.aidev.run/docs" target="_blank" rel="noopener noreferrer">Demo FastApi </a> serving a PDF Assistant.

## Tutorials

### Build an AI App in 3 steps

[![Build an AI App](https://img.youtube.com/vi/VNoBVR5t1yI/0.jpg)](https://www.youtube.com/watch?v=VNoBVR5t1yI&t "Build an AI App")

### Build a Local RAG AI App using OpenHermes and Ollama
[![Local AI App](https://img.youtube.com/vi/EVQLYncsDVI/0.jpg)](https://www.youtube.com/watch?v=EVQLYncsDVI&t "Local AI App")

## More Examples

### Assistant that calls the HackerNews API

<details>

<summary>Show details</summary>

- Create a file `api_assistant.py` that can call the HackerNews API to get top stories.

```python
import json
import httpx

from phi.assistant import Assistant


def get_top_hackernews_stories(num_stories: int = 10) -> str:
    """Use this function to get top stories from Hacker News.

    Args:
        num_stories (int): Number of stories to return. Defaults to 10.

    Returns:
        str: JSON string of top stories.
    """

    # Fetch top story IDs
    response = httpx.get('https://hacker-news.firebaseio.com/v0/topstories.json')
    story_ids = response.json()

    # Fetch story details
    stories = []
    for story_id in story_ids[:num_stories]:
        story_response = httpx.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json')
        story = story_response.json()
        if "text" in story:
            story.pop("text", None)
        stories.append(story)
    return json.dumps(stories)

assistant = Assistant(tools=[get_top_hackernews_stories], show_tool_calls=True)
assistant.print_response("Summarize the top stories on hackernews?", markdown=True)
```

- Run the `api_assistant.py` file

```shell
python api_assistant.py
```

- See it work through the problem

```shell
╭──────────┬───────────────────────────────────────────────────────────────────╮
│ Message  │ Summarize the top stories on hackernews?                          │
├──────────┼───────────────────────────────────────────────────────────────────┤
│ Response │                                                                   │
│ (51.1s)  │  • Running: get_top_hackernews_stories(num_stories=5)             │
│          │                                                                   │
│          │ Here's a summary of the top stories on Hacker News:               │
│          │                                                                   │
│          │  1 Boeing Whistleblower: Max 9 Production Line Has "Enormous      │
│          │    Volume of Defects" A whistleblower has revealed that Boeing's  │
│          │    Max 9 production line is riddled with an "enormous volume of   │
│          │    defects," with instances where bolts were not installed. The   │
│          │    story has garnered attention with a score of 140. Read more    │
│          │  2 Arno A. Penzias, 90, Dies; Nobel Physicist Confirmed Big Bang  │
│          │    Theory Arno A. Penzias, a Nobel Prize-winning physicist known  │
│          │    for his work that confirmed the Big Bang Theory, has passed    │
│          │    away at the age of 90. His contributions to science have been  │
│          │    significant, leading to discussions and tributes in the        │
│          │    scientific community. The news has a score of 207. Read more   │
│          │  3 Why the fuck are we templating YAML? (2019) This provocative   │
│          │    article from 2019 questions the proliferation of YAML          │
│          │    templating in software, sparking a larger conversation about   │
│          │    the complexities and potential pitfalls of this practice. With │
│          │    a substantial score of 149, it remains a hot topic of debate.  │
│          │    Read more                                                      │
│          │  4 Forging signed commits on GitHub Researchers have discovered a │
│          │    method for forging signed commits on GitHub which is causing   │
│          │    concern within the tech community about the implications for   │
│          │    code security and integrity. The story has a current score of  │
│          │    94. Read more                                                  │
│          │  5 Qdrant, the Vector Search Database, raised $28M in a Series A  │
│          │    round Qdrant, a company specializing in vector search          │
│          │    databases, has successfully raised $28 million in a Series A   │
│          │    funding round. This financial milestone indicates growing      │
│          │    interest and confidence in their technology. The story has     │
│          │    attracted attention with a score of 55. Read more              │
╰──────────┴───────────────────────────────────────────────────────────────────╯
```

</details>

### Assistant that generates pydantic models

<details>

<summary>Show details</summary>

One of our favorite features is generating structured data (i.e. a pydantic model) from sparse information.
Meaning we can use Assistants to return pydantic models and generate content which previously could not be possible.
In this example, our movie assistant generates an object of the `MovieScript` class.

- Create a file `pydantic_assistant.py`

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

- Run the `pydantic_assistant.py` file

```shell
python pydantic_assistant.py
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

### A PDF Assistant with Knowledge & Storage

<details>

<summary>Show details</summary>

Lets create a PDF Assistant that can answer questions from a PDF. We'll use `PgVector` for knowledge and storage.

**Knowledge Base:** information that the Assistant can search to improve its responses (uses a vector db).

**Storage:** provides long term memory for Assistants (uses a database).

1. Run PgVector

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
)

# -*- DockerResources
dev_docker_resources = DockerResources(apps=[vector_db])
```

- Start `PgVector` using

```shell
phi start resources.py -y
```

2. Create PDF Assistant

- Create a file `pdf_assistant.py`

```python
import typer
from rich.prompt import Prompt
from typing import Optional, List
from phi.assistant import Assistant
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2

from resources import vector_db

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector2(
        collection="recipes",
        db_url=vector_db.get_db_connection_local(),
    ),
)
# Comment out after first run
knowledge_base.load(recreate=False)

storage = PgAssistantStorage(
    table_name="pdf_assistant",
    db_url=vector_db.get_db_connection_local(),
)


def pdf_assistant(new: bool = False, user: str = "user"):
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
        # use_tools=True adds functions to
        # search the knowledge base and chat history
        use_tools=True,
        show_tool_calls=True,
        # Uncomment the following line to use traditional RAG
        # add_references_to_prompt=True,
    )
    if run_id is None:
        run_id = assistant.run_id
        print(f"Started Run: {run_id}\n")
    else:
        print(f"Continuing Run: {run_id}\n")

    while True:
        message = Prompt.ask(f"[bold] :sunglasses: {user} [/bold]")
        if message in ("exit", "bye"):
            break
        assistant.print_response(message, markdown=True)

if __name__ == "__main__":
    typer.run(pdf_assistant)
```

3. Install libraries

```shell
pip install -U pgvector pypdf psycopg sqlalchemy
```

4. Run PDF Assistant

```shell
python pdf_assistant.py
```

- Ask a question:

```
How do I make pad thai?
```

- See how the Assistant searches the knowledge base and returns a response.

<details>

<summary>Show output</summary>

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

- Message `bye` to exit, start the assistant again using `python pdf_assistant.py` and ask:

```
What was my last message?
```

See how the assistant now maintains storage across sessions.

- Run the `pdf_assistant.py` file with the `--new` flag to start a new run.

```shell
python pdf_assistant.py --new
```

5. Stop PgVector

Play around and then stop `PgVector` using `phi stop resources.py`

```shell
phi stop resources.py -y
```

</details>

### Build an AI App using Streamlit, FastApi and PgVector

<details>

<summary>Show details</summary>

Let's build an **AI App** using GPT-4 as the LLM, Streamlit as the chat interface, FastApi as the API and PgVector for knowledge and storage. Read the full tutorial <a href="https://docs.phidata.com/ai-app/run-local" target="_blank" rel="noopener noreferrer">here</a>.

### Create your codebase

Create your codebase using the `ai-app` template

```shell
phi ws create -t ai-app -n ai-app
```

This will create a folder `ai-app` with a pre-built AI App that you can customize and make your own.

### Serve your App using Streamlit

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
- Ask "How do I make pad thai?"
- Upload PDFs and ask questions

> We provide a default PDF of ThaiRecipes that you can clear using the `Clear Knowledge Base` button. The PDF is only for testing.

<img width="800" alt="chat-with-pdf" src="https://github.com/phidatahq/phidata/assets/22579644/a8eff0ac-963c-43cb-a784-920bd6713a48">

### Optional: Serve your App using FastApi

Streamlit is great for building micro front-ends but any production application will be built using a front-end framework like `next.js` backed by a RestApi built using a framework like `FastApi`.

Your AI App comes ready-to-use with FastApi endpoints.

- Update the `workspace/settings.py` file and set `dev_api_enabled=True`

```python
...
ws_settings = WorkspaceSettings(
    ...
    # Uncomment the following line
    dev_api_enabled=True,
...
```

- Start the `api` group using:

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

### Stop the workspace

Play around and stop the workspace using:

```shell
phi ws down
```

### Run your AI App on AWS

Read how to <a href="https://docs.phidata.com/quickstart/run-aws" target="_blank" rel="noopener noreferrer">run your AI App on AWS</a>.

</details>

### [Checkout the cookbook for more examples](https://github.com/phidatahq/phidata/tree/main/cookbook)

## Documentation

- You can find the full documentation <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">here</a>
- You can also chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a>
- Or email us at <a href="mailto:help@phidata.com" target="_blank" rel="noopener noreferrer">help@phidata.com</a>

## AI Applications

After building an Assistant, serve it using **Streamlit**, **FastApi** or **Django** to build your AI application.
Instead of wiring tools manually, phidata provides **pre-built** templates for AI Apps that you can run locally or deploy to AWS with 1 command. Here's how they work:

- Create your AI App using a template: `phi ws create`
- Run your app locally: `phi ws up`
- Run your app on AWS: `phi ws up prd:aws`

## Building AI for your product?

We've helped many companies build AI for their products, the general workflow is:

1. **Train an assistant** with proprietary data to perform tasks specific to your product.
2. **Connect your product** to the assistant via an API.
3. **Customize, Monitor and Improve** the AI.

We provide dedicated support and development for AI products. [Book a call](https://cal.com/phidata/intro) to get started.

## Contributions

We're an open-source project and welcome contributions, please read the [contributing guide](CONTRIBUTING.md) for more information.

## Request a feature

- If you have a feature request, please open an issue or make a pull request.
- If you have ideas on how we can improve, please create a discussion.

## Roadmap

Our roadmap is available <a href="https://github.com/orgs/phidatahq/projects/2/views/1" target="_blank" rel="noopener noreferrer">here</a>.
If you have a feature request, please open an issue/discussion.
