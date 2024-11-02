from phi.agent import Agent
from phi.model.huggingface import HuggingFaceChat
import os
from getpass import getpass

os.environ['HF_TOKEN'] = getpass("Enter your HuggingFace Access token")

agent = Agent(
    model = HuggingFaceChat(
        id="mistralai/Mistral-7B-Instruct-v0.2",
        max_tokens=4096,
        temperature=0
    ),
    description="What is meaning of life",
)
agent.print_response("What is meaning of life and then recommend 5 best books for the same",stream=True)