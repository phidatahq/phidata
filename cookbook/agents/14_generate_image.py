from phi.agent import Agent
from phi.tools.dalle import Dalle
from phi.model.openai import OpenAIChat

image_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[Dalle()],
    description="You are an AI agent that can generate images using DALL-E.",
    instructions="When the user asks you to create an image, use the `create_image` tool to create the image.",
    markdown=True,
    show_tool_calls=True,
)

image_agent.print_response("Generate an image of a white siamese cat")

images = image_agent.get_images()
if images and isinstance(images, list):
    for image_response in images:
        image_data = image_response.get("data")  # type: ignore
        if image_data:
            for image in image_data:
                image_url = image.get("url")  # type: ignore
                if image_url:
                    print(image_url)
