from phi.agent import Agent
from phi.model.openai import OpenAIChat

task = (
    "Discuss the concept of 'The Ship of Theseus' and its implications on the notions of identity and change. "
    "Present arguments for and against the idea that an object that has had all of its components replaced remains "
    "fundamentally the same object. Conclude with your own reasoned position on the matter."
)

reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"), reasoning=True, markdown=True, structured_outputs=True
)

reasoning_agent.print_response(task, stream=True, show_full_reasoning=True)
