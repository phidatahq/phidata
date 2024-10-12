from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat

task = "How many 'r' are in the word 'supercalifragilisticexpialidocious'?"

# Give a regular agent the task
# agent = Agent(model=OpenAIChat(id="gpt-4o"), markdown=True)
# agent.print_response(task)

# Give a reasoning agent the task
reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"), reasoning=True, markdown=True, structured_outputs=True
)
reasoning_agent.print_response(task, stream=True)
