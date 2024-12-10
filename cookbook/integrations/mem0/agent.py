from mem0 import MemoryClient
from phi.agent import Agent
from phi.model.openai import OpenAIChat

client = MemoryClient()

user_id = "phi"
messages = [
    {"role": "user", "content": "My name is John Billings."},
    {"role": "user", "content": "I live in NYC."},
    {"role": "user", "content": "I'm going to a concert tomorrow."},
]
# Comment out the following line after running the script once
client.add(messages, user_id=user_id)

agent = Agent(model=OpenAIChat(), context={"memory": client.get_all(user_id=user_id)}, add_context=True)
agent.print_response("What do you know about me?", stream=True, markdown=True)
