from agno.agent import Agent
from agno.models.openai import OpenAI

task = "Craft a curriculum for Python 101"

reasoning_agent = Agent(model=OpenAI(id="gpt-4o"), reasoning=True, markdown=True, structured_outputs=True)
reasoning_agent.print_response(task, stream=True, show_full_reasoning=True)
