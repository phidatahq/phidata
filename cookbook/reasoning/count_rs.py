import asyncio

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.cli.console import console

task = "How many 'r' are in the word 'supercalifragilisticexpialidocious'?"

regular_agent = Agent(model=OpenAIChat(id="gpt-4o"), markdown=True)
reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"), reasoning=True, markdown=True, structured_outputs=True
)


async def main():
    console.rule("[bold blue]Async Execution[/bold blue]")

    console.rule("[bold green]Regular Agent Stream (Async)[/bold green]")
    await regular_agent.aprint_response(task, stream=True)
    console.rule("[bold yellow]Reasoning Agent Stream (Async)[/bold yellow]")
    await reasoning_agent.aprint_response(task, stream=True)

    console.rule("[bold green]Regular Agent (Async)[/bold green]")
    await regular_agent.aprint_response(task)
    console.rule("[bold yellow]Reasoning Agent (Async)[/bold yellow]")
    await reasoning_agent.aprint_response(task)


asyncio.run(main())

console.rule("[bold red]Sync Execution[/bold red]")

console.rule("[bold green]Regular Agent Stream (Sync)[/bold green]")
regular_agent.print_response(task, stream=True)
console.rule("[bold yellow]Reasoning Agent Stream (Sync)[/bold yellow]")
reasoning_agent.print_response(task, stream=True)

console.rule("[bold green]Regular Agent (Sync)[/bold green]")
regular_agent.print_response(task)
console.rule("[bold yellow]Reasoning Agent (Sync)[/bold yellow]")
reasoning_agent.print_response(task)
