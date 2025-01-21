<div align="center" id="top">
  <a href="https://docs.agno.com">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".assets/logo.svg">
      <img src=".assets/logo.svg" alt="Agno">
    </picture>
  </a>
</div>
<div align="center">
  Lightning Fast AI Agents
</div>
<div align="center">
  <a href="https://docs.agno.com">📚 Documentation</a> &nbsp;|&nbsp;
  <a href="https://github.com/agno-agi/agno/tree/main/cookbook">💡 Examples</a> &nbsp;|&nbsp;
  <a href="https://github.com/agno-agi/agno/stargazers">🌟 Star Us</a>
</div>

## What is Agno?

[Agno](https://docs.agno.com) is a lightning-fast, model-agnostic framework for building Agents

## Design principles

- **Simplicity**: No graphs, chains, or convoluted patterns — just pure python.
- **Uncompromising Performance**: Blazing fast agents with a minimal memory footprint.
- **Truly Agnostic**: Any model, any provider, any modality. Future-proof agents.

## Key features

- **🚀 Lightning Fast**: Agent creation is 6000x faster than LangGraph (see [performance](#performance)).
- **⚙️ Model Agnostic**: Use any provider, any model-no lock-in.
- **📷 Multi-Modal**: Native support for text, image, audio, and video.
- **🤝 Multi-Agent**: Delegate tasks across a team of specialized agents.
- **🧠 Memory Management**: Store user sessions and context in a database.
- **📚 Knowledge Stores**: Integrate vector databases for Agentic RAG or dynamic few-shot learning.
- **🧩 Structured Outputs**: Respond with structured data.
- **📈 Monitoring**: Track agent sessions and performance in real-time on [agno.com](https://app.agno.com).

## Installation

```shell
pip install -U agno
```

## What are Agents?

Agents are programs that use language models to control the execution flow. They solve problems autonomously by integrating tools, memory, and knowledge.

- **Level 0**: Agents with no tools (basic inference tasks).
- **Level 1**: Agents with tools for autonomous task execution.
- **Level 2**: Agents with knowledge, combining memory and reasoning.
- **Level 3**: Teams of agents collaborating on complex workflows.

## Example - Basic Agent

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

python basic_agent.py
```

[View this example in the cookbook](./cookbook/getting_started/01_basic_agent.py)

This agent will obviously make up a story, lets give it a tool to search the web.

## Example - Agent with tools

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

python agent_with_tools.py
```

Now you should see a much more relevant result.

[View this example in the cookbook](./cookbook/getting_started/02_agent_with_tools.py)

## Example - Agent with knowledge

Agents can store knowledge in a vector database which can be used for RAG or dynamic few-shot. Eg: If you're building a text-to-sql agent, you can store sample queries in the knowledge base and use them to generate better responses.

**Agno agents use Agentic RAG** by default, which means they will search their knowledge base for the specific information they need to achieve their task.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.embedder.openai import OpenAIEmbedder
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType

agent = Agent(
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
if agent.knowledge is not None:
    agent.knowledge.load()

agent.print_response("How do I make chicken and galangal in coconut milk soup", stream=True)
agent.print_response("What is the history of Thai curry?", stream=True)
```

Install dependencies and run the Agent:

```shell
pip install lancedb tantivy pypdf duckduckgo-search

python agent_with_knowledge.py
```

[View this example in the cookbook](./cookbook/getting_started/03_agent_with_knowledge.py)

## Example - Multi Agent Teams

Agents work best when they have a singular purpose, a narrow scope and a small number of tools. When the number of tools grows beyond what the language model can handle or the tools belong to different categories, use a team of agents to achieve the task.

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

python agent_team.py
```

[View this example in the cookbook](./cookbook/getting_started/05_agent_team.py)

## Performance

Agno is built for speed and scale:

- Instantiation: <10μs on average (6000x faster than LangGraph).
- Memory footprint: <40Mib on average (2.6x less memory than LangGraph).

> Tested on an Apple M4 Mackbook Pro.

While an Agent's performance is bottlenecked by inference, we must do all we can to minimize execution time, reduce memory usage, and parallelize tool calls where possible.

### Instantiation time

Let's compare instantiating an Agent with 1 tool using Agno vs LangGraph, we'll run the evaluation 50 times and take the average. You should run the evaluation yourself on your own machine, please, do not take these results at face value.

```shell
pip install openai memory_profiler agno langgraph langchain_openai

# Agno
python evals/performance/instantiation_with_tool.py

# LangGraph
python evals/performance/other/langgraph_instantiation.py
```

The following evaluation is run on an Apple M4 Mackbook Pro, but we'll soon be moving this to a Github actions runner for consistency. LangGraph is on the right, we start it first to minimize bias and Agno is on the left.

https://github.com/user-attachments/assets/712216a4-974a-415e-8849-f77043b7997f

Dividing the average time taken to instantiate a Langgraph Agent by the average time taken to instantiate an Agno Agent:

```
0.020019s / 0.000003s ~ 6673
```

**Agno Agent instantiation is roughly 6000x times faster than Langgraph Agent instantiation**. Sure, the runtime is dominated by inference, but these numbers will add up.

### Memory usage

In the benchmarks above, ~30Mib of memory usage is from the memory profiler, Agno Agents use 66.6 - 30 ~ 36.6Mib of memory. Whereas Langgraph Agents use 125.3 - 30 ~ 95.3Mib of memory. Langgraph Agents use ~2.6x more memory than Agno Agents. When you're running 1000s of Agents in production, these numbers will add up.

> We understand that these aren't the most accurate benchmarks, but we are planning on publishing accuracy, reliability and performance benchmarks running on Github actions in the coming weeks.

## Documentation, Community & More examples

- Docs: <a href="https://docs.agno.com" target="_blank" rel="noopener noreferrer">docs.agno.com</a>
- Getting Started Examples: <a href="https://github.com/agno-agi/agno/tree/main/cookbook/getting_started" target="_blank" rel="noopener noreferrer">Getting Started Cookbook</a>
- All Examples: <a href="https://github.com/agno-agi/agno/tree/main/cookbook" target="_blank" rel="noopener noreferrer">Cookbook</a>
- Community forum: <a href="https://community.agno.com/" target="_blank" rel="noopener noreferrer">community.agno.com</a>
- Chat: <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">discord</a>

## Contributions

We welcome contributions, read our [contributing guide](https://github.com/agno-agi/agno/blob/main/CONTRIBUTING.md) to get started.

## Telemetry

Agno logs which model an agent used so we can prioritize updates to the most popular providers. You can disable this by setting `AGNO_TELEMETRY=false` in your environment.

<p align="left">
  <a href="#top">⬆️ Back to Top</a>
</p>
