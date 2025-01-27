from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat

task = "Plan an itinerary from Los Angeles to Las Vegas"

reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    reasoning_model=Groq(
        id="deepseek-r1-distill-llama-70b", temperature=0.6, max_tokens=1024, top_p=0.95
    ),
    markdown=True,
)
reasoning_agent.print_response(task, stream=True)
