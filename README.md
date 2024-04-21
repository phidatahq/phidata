<h1 align="center">
  phidata
</h1>

<h3 align="center">
Phidata is a framework for building AI Assistants with memory, knowledge and tools.
</h3>

![image](https://github.com/phidatahq/phidata/assets/22579644/295187f6-ac9d-41e0-abdb-38e3291ad1d1)

## Why phidata

**Problem:** LLMs have limited context and cannot take actions.<br />
**Solution:** Add memory, knowledge and tools.
- **Memory:** Enables LLMs to have long-term conversations by storing **chat history** in a database.
- **Knowledge:** Provides LLMs with **business context** by storing information in a vector database.
- **Tools:** Enable LLMs to **take actions** like pulling data from an API, sending emails or querying a database.

Memory & knowledge make LLMs **smarter** while tools make them **autonomous**.

## How it works

- **Step 1:** Create an `Assistant`
- **Step 2:** Add Tools (functions), Knowledge (vectordb) and Storage (database)
- **Step 3:** Serve using Streamlit, FastApi or Django to build your AI application


## Installation

```shell
pip install -U phidata
```

## Example: Assistant that can search the web

Create a file `assistant.py`

```python
from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(tools=[DuckDuckGo()], show_tool_calls=True)
assistant.print_response("Whats happening in France?", markdown=True)
```

Install libraries

```shell
pip install openai duckduckgo-search
```

Export your OPENAI_API_KEY

```shell
export OPENAI_API_KEY=sk-xxxx
```

Run the `Assistant` and let it search the web using `DuckDuckGo`

```shell
python assistant.py
```

## Next Steps

1. Read the <a href="https://docs.phidata.com/basics" target="_blank" rel="noopener noreferrer">basics</a> to learn more about phidata.
2. Read about <a href="https://docs.phidata.com/assistants/introduction" target="_blank" rel="noopener noreferrer">Assistants</a> and how to customize them.
3. Checkout the <a href="https://docs.phidata.com/examples/cookbook" target="_blank" rel="noopener noreferrer">cookbook</a> for in-depth examples and code.

## Documentation

- You can find the full documentation <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">here</a>
- You can also chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a>

## Demos

Checkout the following AI Applications built using phidata:

- <a href="https://pdf.aidev.run/" target="_blank" rel="noopener noreferrer">PDF AI</a> that summarizes and answers questions from PDFs.
- <a href="https://arxiv.aidev.run/" target="_blank" rel="noopener noreferrer">ArXiv AI</a> that answers questions about ArXiv papers using the ArXiv API.
- <a href="https://hn.aidev.run/" target="_blank" rel="noopener noreferrer">HackerNews AI</a> summarize stories, users and shares what's new on HackerNews.

## More Examples

### Assistant that can write and run python code

<details>

<summary>Show details</summary>

The `PythonAssistant` can achieve tasks by writing and running python code.

- Create a file `python_assistant.py`

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

- Install pandas and run the `python_assistant.py`

```shell
pip install pandas

python python_assistant.py
```

</details>

### Assistant that can analyze data using SQL

<details>

<summary>Show details</summary>

The `DuckDbAssistant` can perform data analysis using SQL.

- Create a file `data_assistant.py`

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

- Install duckdb and run the `data_assistant.py` file

```shell
pip install duckdb

python data_assistant.py
```

</details>

### Assistant that can generate pydantic models

<details>

<summary>Show details</summary>

One of our favorite LLM features is generating structured data (i.e. a pydantic model) from text. Use this feature to extract features, generate movie scripts, produce fake data etc.

Let's create an Movie Assistant to write a `MovieScript` for us.

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
    description="You help write movie scripts.",
    output_model=MovieScript,
)

pprint(movie_assistant.run("New York"))
```

- Run the `movie_assistant.py` file

```shell
python movie_assistant.py
```

- The output is an object of the `MovieScript` class, here's how it looks:

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

### PDF Assistant with Knowledge & Storage

<details>

<summary>Show details</summary>

Lets create a PDF Assistant that can answer questions from a PDF. We'll use `PgVector` for knowledge and storage.

**Knowledge Base:** information that the Assistant can search to improve its responses (uses a vector db).

**Storage:** provides long term memory for Assistants (uses a database).

1. Run PgVector

Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) and run **PgVector** on port **5532** using:

```bash
docker run -d \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 \
  --name pgvector \
  phidata/pgvector:16
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

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector2(collection="recipes", db_url=db_url),
)
# Comment out after first run
knowledge_base.load()

storage = PgAssistantStorage(table_name="pdf_assistant", db_url=db_url)


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
        # Show tool calls in the response
        show_tool_calls=True,
        # Enable the assistant to search the knowledge base
        search_knowledge=True,
        # Enable the assistant to read the chat history
        read_chat_history=True,
    )
    if run_id is None:
        run_id = assistant.run_id
        print(f"Started Run: {run_id}\n")
    else:
        print(f"Continuing Run: {run_id}\n")

    # Runs the assistant as a cli app
    assistant.cli_app(markdown=True)


if __name__ == "__main__":
    typer.run(pdf_assistant)
```

3. Install libraries

```shell
pip install -U pgvector pypdf "psycopg[binary]" sqlalchemy
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

- Message `bye` to exit, start the assistant again using `python pdf_assistant.py` and ask:

```
What was my last message?
```

See how the assistant now maintains storage across sessions.

- Run the `pdf_assistant.py` file with the `--new` flag to start a new run.

```shell
python pdf_assistant.py --new
```

</details>

### Checkout the [cookbook](https://github.com/phidatahq/phidata/tree/main/cookbook) for more examples.

## Tutorials

### Build an AI App in 3 steps

[![Build an AI App](https://img.youtube.com/vi/VNoBVR5t1yI/0.jpg)](https://www.youtube.com/watch?v=VNoBVR5t1yI&t "Build an AI App")

### Build a Local RAG AI App using OpenHermes and Ollama
[![Local AI App](https://img.youtube.com/vi/EVQLYncsDVI/0.jpg)](https://www.youtube.com/watch?v=EVQLYncsDVI&t "Local AI App")

## Looking to build an AI product?

We've helped many companies build AI products, the general workflow is:

1. **Build an Assistant** with proprietary data to perform tasks specific to your product.
2. **Connect your product** to the Assistant via an API.
3. **Monitor and Improve** your AI product.

We also provide dedicated support and development, [book a call](https://cal.com/phidata/intro) to get started.

## Contributions

We're an open-source project and welcome contributions, please read the [contributing guide](CONTRIBUTING.md) for more information.

## Request a feature

- If you have a feature request, please open an issue or make a pull request.
- If you have ideas on how we can improve, please create a discussion.

## Roadmap

Our roadmap is available <a href="https://github.com/orgs/phidatahq/projects/2/views/1" target="_blank" rel="noopener noreferrer">here</a>.
If you have a feature request, please open an issue/discussion.
