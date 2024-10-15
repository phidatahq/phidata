<h1 align="center">
  phidata
</h1>

<h3 align="center">
Build AI Agents with memory, knowledge, tools and reasoning
</h3>

![image](https://github.com/phidatahq/phidata/assets/22579644/295187f6-ac9d-41e0-abdb-38e3291ad1d1)

## What is phidata?

**Phidata is a framework for building agentic systems**, use phidata to:

- **Build powerful AI Agents with memory, knowledge, tools and reasoning.**
- **Run those agents as a software application (with a database, vectordb and api).**
- **Monitor, evaluate and optimize your agentic system.**

Let's start by building some agents.

## Installation

```shell
pip install -U phidata
```

## Quickstart

### Agent that can search the web

Create a file `web_search.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=OpenAIChat(id="gpt-4o"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
```

Install libraries, export your `OPENAI_API_KEY` and run the `Agent`

```shell
pip install openai duckduckgo-search

export OPENAI_API_KEY=sk-xxxx

python web_search.py
```

### Agent that can query financial data

Create a file `finance_agent.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Use tables where possible"],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("What is the stock price of NVDA", stream=True)
agent.print_response("Write a comparison between NVDA and AMD, use all tools available.")
```

Install libraries and run the `Agent`

```shell
pip install yfinance

python finance_agent.py
```

### Agent that can reason

Reasoning helps agents work through a problem step-by-step, backtracking and correcting as needed. Let's give the reasonining agent a simple task that gpt-4o fails at.

Create a file `basic_reasoning.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.cli.console import console

regular_agent = Agent(model=OpenAIChat(id="gpt-4o"), markdown=True)
reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"),
    reasoning=True,
    markdown=True,
    structured_outputs=True,
)

task = "How many 'r' are in the word 'supercalifragilisticexpialidocious'?"

console.rule("[bold green]Regular Agent[/bold green]")
regular_agent.print_response(task, stream=True)
console.rule("[bold yellow]Reasoning Agent[/bold yellow]")
reasoning_agent.print_response(task, stream=True, show_full_reasoning=True)
```

Run the `Agent`

```shell
python basic_reasoning.py
```

## More information

- Read the docs at <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">docs.phidata.com</a>
- Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a>

## More examples

### Agent that can write and run python code

<details>

<summary>Show code</summary>

The `PythonAgent` can achieve tasks by writing and running python code.

- Create a file `python_agent.py`

```python
from phi.agent.python import PythonAgent
from phi.model.openai import OpenAIChat
from phi.file.local.csv import CsvFile

python_agent = PythonAgent(
    model=OpenAIChat(id="gpt-4o"),
    files=[
        CsvFile(
            path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
            description="Contains information about movies from IMDB.",
        )
    ],
    markdown=True,
    pip_install=True,
    show_tool_calls=True,
)

python_agent.print_response("What is the average rating of movies?")
```

- Install pandas and run the `python_agent.py`

```shell
pip install pandas

python python_agent.py
```

</details>

### Agent that can analyze data using SQL

<details>

<summary>Show code</summary>

The `DuckDbAgent` can perform data analysis using SQL.

- Create a file `data_analyst.py`

```python
import json
from phi.model.openai import OpenAIChat
from phi.agent.duckdb import DuckDbAgent

data_analyst = DuckDbAgent(
    model=OpenAIChat(model="gpt-4o"),
    markdown=True,
    semantic_model=json.dumps(
        {
            "tables": [
                {
                    "name": "movies",
                    "description": "Contains information about movies from IMDB.",
                    "path": "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
                }
            ]
        },
        indent=2,
    ),
)

data_analyst.print_response(
    "Show me a histogram of ratings. "
    "Choose an appropriate bucket size but share how you chose it. "
    "Show me the result as a pretty ascii diagram",
    stream=True,
)
```

- Install duckdb and run the `data_analyst.py` file

```shell
pip install duckdb

python data_analyst.py
```

</details>

### Agent that can generate pydantic models

<details>

<summary>Show code</summary>

One of our favorite LLM features is generating structured data (i.e. a pydantic model) from text. Use this feature to extract features, generate movie scripts, produce fake data etc.

Let's create a Movie Agent to write a `MovieScript` for us.

- Create a file `movie_agent.py`

```python
from typing import List
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from pydantic import BaseModel, Field

class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(..., description="Genre of the movie. If not available, select action, thriller or romantic comedy.")
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")

# Agent that uses JSON mode
json_mode_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You write movie scripts.",
    response_model=MovieScript,
)

# Agent that uses structured outputs
structured_output_agent = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"),
    description="You write movie scripts.",
    response_model=MovieScript,
    structured_outputs=True,
)

json_mode_agent.print_response("New York")
structured_output_agent.print_response("New York")
```

- Run the `movie_agent.py` file

```shell
python movie_agent.py
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

### Checkout the [cookbook](https://github.com/phidatahq/phidata/tree/main/cookbook) for more examples.

## Contributions

We're an open-source project and welcome contributions, please read the [contributing guide](https://github.com/phidatahq/phidata/blob/main/CONTRIBUTING.md) for more information.

## Request a feature

- If you have a feature request, please open an issue or make a pull request.
- If you have ideas on how we can improve, please create a discussion.
