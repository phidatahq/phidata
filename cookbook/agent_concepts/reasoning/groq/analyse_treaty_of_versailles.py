from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat

task = (
    "Analyze the key factors that led to the signing of the Treaty of Versailles in 1919. "
    "Discuss the political, economic, and social impacts of the treaty on Germany and how it "
    "contributed to the onset of World War II. Provide a nuanced assessment that includes "
    "multiple historical perspectives."
)

reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    reasoning_model=Groq(
        id="deepseek-r1-distill-llama-70b", temperature=0.6, max_tokens=1024, top_p=0.95
    ),
    markdown=True,
)
reasoning_agent.print_response(task, stream=True)
