from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat

task = (
    "You are a philosopher tasked with analyzing the classic 'Trolley Problem'. In this scenario, a runaway trolley "
    "is barreling down the tracks towards five people who are tied up and unable to move. You are standing next to "
    "a large stranger on a footbridge above the tracks. The only way to save the five people is to push this stranger "
    "off the bridge onto the tracks below. This will kill the stranger, but save the five people on the tracks. "
    "Should you push the stranger to save the five people? Provide a well-reasoned answer considering utilitarian, "
    "deontological, and virtue ethics frameworks. "
    "Include a simple ASCII art diagram to illustrate the scenario."
)

reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    reasoning_model=Groq(
        id="deepseek-r1-distill-llama-70b", temperature=0.6, max_tokens=1024, top_p=0.95
    ),
    markdown=True,
)
reasoning_agent.print_response(task, stream=True)
