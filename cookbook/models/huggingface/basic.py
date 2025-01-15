from agno.agent import Agent
from agno.models.huggingface import HuggingFaceChat

agent = Agent(
    model=HuggingFaceChat(id="mistralai/Mistral-7B-Instruct-v0.2", max_tokens=4096, temperature=0),
)
agent.print_response("What is meaning of life and then recommend 5 best books to read about it")
