import asyncio
import time

from agno.agent import Agent
from agno.models.openai import OpenAIChat


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


def task3(delay: int):
    """Simulate a task that takes a random amount of time to complete
    Args:
        delay (int): The amount of time to delay the task
    """
    time.sleep(delay)
    return f"Task 3 completed in {delay:.2f}s"


agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[task2, task1, task3],
    show_tool_calls=True,
    markdown=True,
)
# Non-streaming response
asyncio.run(agent.aprint_response("Please run all tasks with a delay of 5s"))
# Streaming response
# asyncio.run(
#     agent.aprint_response("Please run all tasks with a delay of 5s", stream=True)
# )
