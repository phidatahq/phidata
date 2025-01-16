<h1 align="center" id="top">
Agno: High Performance AI Agents
</h1>

<p align="center">
  <a href="https://docs.agno.com">📚 Documentation</a> &nbsp;|&nbsp;
  <a href="https://github.com/agno-agi/agno/tree/main/cookbook">💡 Examples</a> &nbsp;|&nbsp;
  <a href="https://github.com/agno-agi/agno/stargazers">🌟 Star Us</a>
</p>

## Overview

[Agno](https://docs.agno.com) is an Agent framework designed for performance and scale. Agno agents are model-agnostic, multi-modal and come with built-in memory, knowledge and session management.

**Agno gets the fundamentals right:** Build performant agents with a minimal memory footprint, reliable tool calling, session, memory and knowledge management. Agno lets the developer design the workflow in pure python. No graphs, no chains, no random patterns that you have to learn or fight against. Want cycles, use loops; want conditions, use if/else; want error handling, use try/except.

**Agno is feature complete:** Agno, previously phidata, was in active development for 2 years and is used in production at 100s of companies.  We’re mostly feature complete and are now focused on reliability and usability. We’ll continue to add integrations, fix bugs and improve performance but our core focus is to provide the best agent development experience and stability and reliability are at the heart of that.

## Key Features

- **Lightning Fast**: Agents instantiate in <10μs on M4 chips (more details below)
- **Model Agnostic**: Use any provider, any model
- **Multi Modal**: Native support for Text, Image, Audio and Video
- **Multi Agent**: Agents can delegate tasks to a team of agents
- **Memory**: Store session and user memories in any database
- **Knowledge**: Store knowledge in any vectordb, use for Agentic RAG or dynamic few-shot
- **Reasoning**: Agents can work through problems step-by-step, backtracking and correcting as needed
- **Evals**: Measure Agent performance and accuracy
- **Structured Outputs**: Agents can respond with a structured output using a Pydantic model
- **Pre-built tools**: Agno currently has 60+ toolkits and integrations with more added every week
- **Monitoring**: Monitor Agent sessions and performance on [agno.com](https://www.agno.com)

## Install

```shell
pip install -U agno
```

## What are Agents?

Agents are programs where a language model controls the flow of execution. Instead of forcing ourselves into a binary definition, we recommend looking at Agents through the lens of Agency and Autonomy.

## Level 0: Agent with no tools

The simplest agent makes a call to a language model and returns the response.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You are an enthusiastic news reporter with a flair for storytelling!",
    markdown=True
)
agent.print_response("Tell me about a breaking news story from New York.", stream=True)
```

Install dependencies, export your `OPENAI_API_KEY` and run the Agent:

```shell
pip install agno openai

export OPENAI_API_KEY=sk-xxxx

python 00_simple_agent.py
```

This agent will obviously make up the story, lets give it a tool to search the web.

## Level 1: Agent with tools

We start to see the power of Agents by giving them tools to achieve their goals. This agent will search the web and generate the response.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You are an enthusiastic news reporter with a flair for storytelling!",
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True
)
agent.print_response("Tell me about a breaking news story from New York.", stream=True)
```

Install dependencies and run the Agent:

```shell
pip install duckduckgo-search

python 01_agent_with_tools.py
```

## Level 2: Agent with knowledge

The next level of agency comes from giving the agent knowledge. We store knowledge in a vector database which can be used for RAG or dynamic few-shot. Eg: If you're building a text-to-sql agent, you can store sample queries in the knowledge base and use it to generate better SQL queries.

**Agno agents use Agentic RAG** by default, which means they will search their knowledge base for the specific information they need to achieve their task. In this example, the agent will search the knowledge base for Thai recipes but if the question is better suited for the web or it doesn't find the information in the knowledge base, it will search the web to fill in gaps.

Agno supports all major vectordbs and embedding models, with more integrations added every week. This example uses LanceDB and the `text-embedding-3-small` embedding model.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.embedder.openai import OpenAIEmbedder
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType

level_2_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You are a Thai cuisine expert!",
    instructions=[
        "Search your knowledge base for Thai recipes.",
        "If the question is better suited for the web, search the web to fill in gaps.",
        "Prefer the information in your knowledge base over the web results."
    ],
    knowledge=PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=LanceDb(
            uri="tmp/lancedb",
            table_name="recipes",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(model="text-embedding-3-small"),
        ),
    ),
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True
)

# Comment out after first run
if level_2_agent.knowledge is not None:
    level_2_agent.knowledge.load()

level_2_agent.print_response("How do I make chicken and galangal in coconut milk soup", stream=True)
level_2_agent.print_response("What is the history of Thai curry?", stream=True)
```

Install dependencies and run the Agent:

```shell
pip install lancedb tantivy pypdf duckduckgo-search

python 02_agent_with_knowledge.py
```

## Level 3: Multi Agent Teams

Agents work best when they have a singular purpose, a narrow scope and a small number of tools. When the number of tools grows beyond what the language model can handle or the tools belong to different categories, we recommend using a team of agents to achieve the task. As complexity grows:
- Split functionality into specialized agents
- Group related tools together (e.g., one agent for web searches, another for financial analysis)
- Create teams of agents that can collaborate on complex tasks

This approach improves reliability, makes debugging easier, and helps prevent cognitive overload on the language model.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions="Always include sources",
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
    instructions="Use tables to display data",
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

agent_team.print_response("What's the market outlook and financial performance of AI semiconductor companies?", stream=True)
```

Install dependencies and run the Agent team:

```shell
pip install duckduckgo-search yfinance

python 03_agent_team.py
```

## Performance

Performance is a key focus for Agno. While the Agent's performance is bottlenecked by inference, as engineers all we can do is minimize agent instantiation time, reduce memory usage, and parallelize tool calls whenever possible.

### Instantiation time

Let's compare instantiating an Agent with 1 tool on Agno vs LangGraph, we'll run the evaluation 50 times and print the results. You should run the evaluation yourself, please, do not take the results here at face value.

```shell
pip install openai memory_profiler agno langgraph langchain_openai

# Agno
python evals/performance/instantiation_with_tool.py

# LangGraph
python evals/performance/other/langgraph_instantiation.py
```

The following evaluation is run on an Apple M4 Mackbook Pro, but we'll soon be moving this to a github actions runner. LangGraph is on the right, we start it first to minimize bias and Agno is on the left.

https://github.com/user-attachments/assets/712216a4-974a-415e-8849-f77043b7997f

Dividing the average time taken to instantiate a Langgraph Agent by the average time taken to instantiate an Agno Agent:

```
0.020019s / 0.000003s ~ 6673
```

So, **Agno Agent instantiation is roughly 6000x times faster than Langgraph Agent instantiation**.

### Memory usage

The memory footprint of an Agent is a key factor in scaling your application. In the benchmarks above, ~30Mib of memory usage is from the memory profiler, Agno Agents use 66.6 - 30 ~ 36.6Mib of memory. Whereas Langgraph Agents use 125.3 - 30 ~ 95.3Mib of memory. Langgraph Agents use 2.6x more memory than Agno Agents.

When you're running 1000s of Agents in production, these numbers add up. We'll publish accuracy, reliability and performance benchmarks in the coming weeks as well.

## Documentation, Community & More examples

- Our documentation is available at <a href="https://docs.agno.com" target="_blank" rel="noopener noreferrer">docs.agno.com</a>
- More examples are available in the [cookbook](https://github.com/agno-agi/agno/tree/main/cookbook)
- If you have any questions, post them on the [community forum](https://community.agno.com/)
- Or chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a>

## Contributions

We welcome contributions, please read the [contributing guide](https://github.com/agno-agi/agno/blob/main/CONTRIBUTING.md) for more information.

## Telemetry

Agno logs which model an agent used so we can prioritize updates to the most popular providers.

You can disable this by setting `AGNO_TELEMETRY=false` in your environment.

<p align="left">
  <a href="#top">⬆️ Back to Top</a>
</p>
