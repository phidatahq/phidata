from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.dalle import DalleTools

agent = Agent(
    # system_prompt="Only return the image URL in your response given by DALL-E.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DalleTools()],
    markdown=True,
    debug_mode=True,
    instructions=[
        "You are an AI agent that can generate images using DALL-E.",
        "DALL-E will return an image URL.",
        "Return it in your response.",
    ],
)

agent.print_response("Generate an image of a white siamese cat")
