import asyncio

from phi.agent import Agent
from phi.model.openai import OpenAIChat


async def task1(delay: int):
    """Simulate a task that takes a random amount of time to complete
    Args:
        delay (int): The amount of time to delay the task
    """
    await asyncio.sleep(delay)
    return f"Task 1 completed in {delay:.2f}s"


async def task2(delay: int):
    """Simulate a task that takes a random amount of time to complete
    Args:
        delay (int): The amount of time to delay the task
    """
    await asyncio.sleep(delay)
    return f"Task 2 completed in {delay:.2f}s"


agent = Agent(model=OpenAIChat(id="gpt-4o"), tools=[task2, task1], async_tools=True)
asyncio.run(agent.aprint_response("Please run both tasks with a delay of 2s", markdown=True))
