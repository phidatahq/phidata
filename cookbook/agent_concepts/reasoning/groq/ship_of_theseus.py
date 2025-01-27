from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat

task = (
    "Discuss the concept of 'The Ship of Theseus' and its implications on the notions of identity and change. "
    "Present arguments for and against the idea that an object that has had all of its components replaced remains "
    "fundamentally the same object. Conclude with your own reasoned position on the matter."
)

reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    reasoning_model=Groq(
        id="deepseek-r1-distill-llama-70b", temperature=0.6, max_tokens=1024, top_p=0.95
    ),
    markdown=True,
)
reasoning_agent.print_response(task, stream=True)
