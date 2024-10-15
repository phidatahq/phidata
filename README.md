<h1 align="center">
  phidata
</h1>

<h3 align="center">
Build AI Agents with memory, knowledge, tools and reasoning
</h3>

<img
  src="https://github.com/user-attachments/assets/21a0b5af-b458-4632-b09d-3cf29566890c"
  style="border-radius: 8px;"
/>


## What is phidata?

**Phidata is a framework for building agentic systems**, use phidata to:

- **Build powerful AI Agents with memory, knowledge, tools and reasoning.**
- **Run those agents as a software application (with a database, vectordb and api).**
- **Monitor, evaluate and optimize your agentic system.**

## Install

```shell
pip install -U phidata
```

## Agents

### Web Search Agent

Let's start by building a simple agent that can search the web, create a file `web_search.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    markdown=True,
    show_tool_calls=True,
)
web_agent.print_response("Whats happening in France?", stream=True)
```

Install libraries, export your `OPENAI_API_KEY` and run the Agent:

```shell
pip install phidata openai duckduckgo-search

export OPENAI_API_KEY=sk-xxxx

python web_search.py
```

### Finance Agent

Lets create another agent that can query financial data, create a file `finance_agent.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Always use tables to display data"],
    markdown=True,
    show_tool_calls=True,
)

finance_agent.print_response("Share analyst recommendations for NVDA", stream=True)
```

Install libraries and run the Agent:

```shell
pip install yfinance

python finance_agent.py
```

## Team of Agents

Now lets create a team of agents using the agents above, create a file `agent_team.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.yfinance import YFinanceTools

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    markdown=True,
    show_tool_calls=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Always use tables to display data"],
    markdown=True,
    show_tool_calls=True,
)

agent_team = Agent(
    team=[web_agent, finance_agent],
    show_tool_calls=True,
    markdown=True,
)

agent_team.print_response("Research the web for NVDA and share analyst recommendations", stream=True)
```

Run the Agent team:

```shell
python agent_team.py
```

## Reasoning Agents

Reasoning helps agents work through a problem step-by-step, backtracking and correcting as needed. Let's give the reasonining agent a simple task that gpt-4o fails at. Create a file `reasoning_agent.py`

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

Run the Reasoning Agent:

```shell
python reasoning_agent.py
```

## Agent Playground

Phidata includes a playground for testing and iterating on agents. Create a file `agent_playground.py`

> Note: Phidata does not store any data, all agent data is stored locally in a sqlite database.

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.storage.agent.sqlite import SqlAgentStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.yfinance import YFinanceTools
from phi.playground import Playground, serve_playground_app

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    storage=SqlAgentStorage(table_name="web_agent"),
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Always use tables to display data"],
    storage=SqlAgentStorage(table_name="finance_agent"),
    markdown=True,
)

app = Playground(agents=[finance_agent, web_agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("serve:app", reload=True)
```

Authenticate with phidata:

```
phi auth
```

Install dependencies and run the Agent Playground:

```
pip install 'fastapi[standard]'

python agent_playground.py
```

- Open your link provided or navigate to `http://phidata.app/playground`
- Select your endpoint, agent and chat with them!

## Monitoring Agents

Phidata comes with monitoring built in. You can manually set `monitoring=True` on any agent or set `PHI_MONITORING=true` in your environment.

> Note: Monitoring requires `phi auth` to be run first.

```python
from phi.agent import Agent

agent = Agent(markdown=True, monitoring=True)
agent.print_response("Share a 2 sentence horror story")
```

Run the agent and monitor the results on [phidata.app/sessions](https://www.phidata.app/sessions)

```shell
# You can also set the environment variable
# export PHI_MONITORING=true

python agent_monitor.py
```

View the agent session on [phidata.app/sessions](https://www.phidata.app/sessions)

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

### Agent that can generate structured outputs

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
