import asyncio

from phi.agent import Agent
from phi.model.openai import OpenAIChat

task = "Give me steps to write a python script for fibonacci series"

reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"), reasoning=True, markdown=True, structured_outputs=True
)


async def main():
    await reasoning_agent.aprint_response(task, stream=True, show_full_reasoning=True)


asyncio.run(main())
