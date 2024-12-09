from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.dalle import Dalle

image_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[Dalle()],
    description="You are an AI agent that can generate images using DALL-E.",
    instructions=[
        "When the user asks you to create an image, use the `create_image` tool to create the image.",
        "The image will be displayed in the UI automatically below your response, so you don't need to show the image URL in your response.",
        "Politely and courteously let the user know that the image has been generated and will be displayed below as soon as its ready.",
    ],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
)

image_agent.print_response("Generate an image of a white siamese cat")
# print(image_agent.run_response.images)
# print(image_agent.get_images())
