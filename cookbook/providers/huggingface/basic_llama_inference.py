from phi.agent import Agent
from phi.model.huggingface import HuggingFaceChat
import os
from getpass import getpass

os.environ['HF_TOKEN'] = getpass("Enter your HuggingFace Access token")

agent = Agent(
    model = HuggingFaceChat(
        id="meta-llama/Meta-Llama-3-8B-Instruct",
        max_tokens=4096,
    ),
    description = "Essay Writer. Write 300 words essage on topic that will be provided by user",
)
agent.print_response("topic: AI")