<h1 align="center" id="top">
  phidata
</h1>

<p align="center">
  <a href="https://docs.phidata.com">
    <img src="https://img.shields.io/badge/Read%20the%20Documentation-Click%20Here-green?style=for-the-badge&logo=read-the-docs" alt="Read the Docs">
  </a>
</p>

<h3 align="center">
Build multi-modal Agents with memory, knowledge and tools
</h3>

<img
  src="https://github.com/user-attachments/assets/44739d09-2ec4-49b7-bea1-b275afccc592"
  style="border-radius: 8px;"
/>

## What is phidata?

**Phidata is a framework for building multi-modal agents**, use phidata to:

- **Build multi-modal agents with memory, knowledge and tools.** [examples](#web-search-agent)
- **Build teams of agents that can work together to solve complex problems.** [example](#team-of-agents)
- **Chat with your agents using a beautiful Agent UI.** [example](#agent-ui)
- **Monitor, evaluate and optimize your agents.** [example](#monitoring)
- **Build agentic systems i.e. applications with an API, database and vectordb.**

## Install

```shell
pip install -U phidata
```

## Agents

### Web Search Agent

Let's start by building a simple agent that can search the web using DuckDuckGo, create a file `web_search.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

web_agent = Agent(
    name="Web Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True,
)
web_agent.print_response("Tell me about OpenAI Sora?", stream=True)
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
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Use tables to display data"],
    show_tool_calls=True,
    markdown=True,
)
finance_agent.print_response("Summarize analyst recommendations for NVDA", stream=True)
```

Install libraries and run the Agent:

```shell
pip install yfinance

python finance_agent.py
```

### Image Agent

Lets create another agent that can understand images and make tool calls as needed, create a file `image_agent.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    markdown=True,
)

agent.print_response(
    "Tell me about this image and give me the latest news about it.",
    images=[
        "https://upload.wikimedia.org/wikipedia/commons/b/bf/Krakow_-_Kosciol_Mariacki.jpg",
    ],
    stream=True,
)
```

Run the Agent:

```shell
python image_agent.py
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
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
    instructions=["Use tables to display data"],
    show_tool_calls=True,
    markdown=True,
)

agent_team = Agent(
    team=[web_agent, finance_agent],
    model=OpenAIChat(id="gpt-4o"),
    instructions=["Always include sources", "Use tables to display data"],
    show_tool_calls=True,
    markdown=True,
)

agent_team.print_response("Summarize analyst recommendations and share the latest news for NVDA", stream=True)
```

Run the Agent team:

```shell
python agent_team.py
```

## Agentic RAG

Instead of always inserting the "context" into the prompt, the RAG Agent can search its knowledge base (vector db) for the specific information it needs to achieve its task.

This saves tokens and improves response quality. Create a file `rag_agent.py`

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.embedder.openai import OpenAIEmbedder
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.lancedb import LanceDb, SearchType

# Create a knowledge base from a PDF
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    # Use LanceDB as the vector database
    vector_db=LanceDb(
        table_name="recipes",
        uri="tmp/lancedb",
        search_type=SearchType.vector,
        embedder=OpenAIEmbedder(model="text-embedding-3-small"),
    ),
)
# Comment out after first run as the knowledge base is loaded
knowledge_base.load()

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    # Add the knowledge base to the agent
    knowledge=knowledge_base,
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("How do I make chicken and galangal in coconut milk soup", stream=True)
```

Install libraries and run the Agent:

```shell
pip install lancedb tantivy pypdf sqlalchemy

python rag_agent.py
```

## Agent UI

Phidata provides a beautiful UI for interacting with your agents. Let's take it for a spin, create a file `playground.py`

![agent_playground](https://github.com/user-attachments/assets/546ce6f5-47f0-4c0c-8f06-01d560befdbc)

> [!NOTE]
> Phidata does not store any data, all agent data is stored locally in a sqlite database.

```python
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.storage.agent.sqlite import SqlAgentStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.yfinance import YFinanceTools
from phi.playground import Playground, serve_playground_app

web_agent = Agent(
    name="Web Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    storage=SqlAgentStorage(table_name="web_agent", db_file="agents.db"),
    add_history_to_messages=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Use tables to display data"],
    storage=SqlAgentStorage(table_name="finance_agent", db_file="agents.db"),
    add_history_to_messages=True,
    markdown=True,
)

app = Playground(agents=[finance_agent, web_agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("playground:app", reload=True)
```

Authenticate with phidata:

```
phi auth
```

> [!NOTE]
> If `phi auth` fails, you can set the `PHI_API_KEY` environment variable by copying it from [phidata.app](https://www.phidata.app)

Install dependencies and run the Agent Playground:

```
pip install 'fastapi[standard]' sqlalchemy

python playground.py
```

- Open the link provided or navigate to `http://phidata.app/playground`
- Select the `localhost:7777` endpoint and start chatting with your agents!

<video
  src="https://github.com/user-attachments/assets/3a2ff93c-3d2d-4f1a-9573-eee25542e5c4"
  style="border-radius: 8px;"
/>

## Demo Agents

The Agent Playground includes a few demo agents that you can test with. If you have recommendations for other demo agents, please let us know in our [community forum](https://community.phidata.com/).

![demo_agents](https://github.com/user-attachments/assets/329aa15d-83aa-4c6c-88f0-2b0eda257198)

## Monitoring & Debugging

### Monitoring

Phidata comes with built-in monitoring. You can set `monitoring=True` on any agent to track sessions or set `PHI_MONITORING=true` in your environment.

> [!NOTE]
> Run `phi auth` to authenticate your local account or export the `PHI_API_KEY`

```python
from phi.agent import Agent

agent = Agent(markdown=True, monitoring=True)
agent.print_response("Share a 2 sentence horror story")
```

Run the agent and monitor the results on [phidata.app/sessions](https://www.phidata.app/sessions)

```shell
# You can also set the environment variable
# export PHI_MONITORING=true

python monitoring.py
```

View the agent session on [phidata.app/sessions](https://www.phidata.app/sessions)

![Agent Session](https://github.com/user-attachments/assets/45f3e460-9538-4b1f-96ba-bd46af3c89a8)

### Debugging

Phidata also includes a built-in debugger that will show debug logs in the terminal. You can set `debug_mode=True` on any agent to track sessions or set `PHI_DEBUG=true` in your environment.

```python
from phi.agent import Agent

agent = Agent(markdown=True, debug_mode=True)
agent.print_response("Share a 2 sentence horror story")
```

![debugging](https://github.com/user-attachments/assets/c933c787-4a28-4bff-a664-93b29360d9ea)

## Getting help

- Read the docs at <a href="https://docs.phidata.com" target="_blank" rel="noopener noreferrer">docs.phidata.com</a>
- Post your questions on the [community forum](https://community.phidata.com/)
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

- Run the `python_agent.py`

```shell
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

One of our favorite LLM features is generating structured data (i.e. a pydantic model) from text. Use this feature to extract features, generate data etc.

Let's create a Movie Agent to write a `MovieScript` for us, create a file `structured_output.py`

```python
from typing import List
from pydantic import BaseModel, Field
from phi.agent import Agent
from phi.model.openai import OpenAIChat

# Define a Pydantic model to enforce the structure of the output
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

- Run the `structured_output.py` file

```shell
python structured_output.py
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

### Check out the [cookbook](https://github.com/phidatahq/phidata/tree/main/cookbook) for more examples.

## Contributions

We're an open-source project and welcome contributions, please read the [contributing guide](https://github.com/phidatahq/phidata/blob/main/CONTRIBUTING.md) for more information.

## Request a feature

- If you have a feature request, please open an issue or make a pull request.
- If you have ideas on how we can improve, please create a discussion.

## Telemetry

Phidata logs which model an agent used so we can prioritize features for the most popular models.

You can disable this by setting `PHI_TELEMETRY=false` in your environment.

<p align="left">
  <a href="#top">⬆️ Back to Top</a>
</p>
