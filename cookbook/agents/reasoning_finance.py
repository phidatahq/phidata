import asyncio
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.cli.console import console

task = "Write a report on TSLA. Use all the tools available."

finance_agent = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"),
    tools=[YFinanceTools(enable_all=True)],
    show_tool_calls=True,
    markdown=True,
    reasoning=True,
)


async def main():
    await finance_agent.aprint_response(task, stream=True)


console.rule("[bold red]Reasoning Agent[/bold red]")

asyncio.run(main())
