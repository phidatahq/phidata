"""
Deferred MCP Tools
==================
Defer a server's tools behind the model's tool search. The server needs no changes:
MCPTools applies the deferral when it turns the listed tools into Functions.

- `defer_loading=True` defers every tool the server lists.
- `always_loaded_tools=[...]` keeps the tools you use on every turn loaded.
- The searchable-tools index describes the server with `tool_search_description`, or with the
  first paragraph of the instructions the server sends when it connects.
- `use_server_instructions=True` also adds those instructions to the system prompt. They are
  third-party text, so this is off by default.

Tool search runs on OpenAI GPT-5.4+ (`OpenAIResponses`) and Claude Opus 4.5 / Sonnet 4.5 /
Haiku 4.5+; other models load the deferred tools normally.
"""

import asyncio

from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.tools.mcp import MCPTools

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------


async def run_agent(message: str) -> None:
    async with MCPTools(
        transport="streamable-http",
        url="https://docs.agno.com/mcp",
        name="agno_docs",
        defer_loading=True,
        tool_search_description="Agno documentation: concepts, guides and API reference.",
    ) as agno_docs:
        print("Server:", agno_docs.server_name)
        print(
            "Deferred tools:",
            [name for name, f in agno_docs.functions.items() if f.defer_loading],
        )

        agent = Agent(
            model=OpenAIResponses(id="gpt-5.4-mini"),
            tools=[agno_docs],
            markdown=True,
        )
        await agent.aprint_response(input=message, stream=True)


# ---------------------------------------------------------------------------
# Run Agent
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(
        run_agent(
            "What is a Team in Agno, and when should I use one instead of a single Agent?"
        )
    )
