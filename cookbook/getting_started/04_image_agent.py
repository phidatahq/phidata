"""🗽 NYC Image Reporter Bot - Your Visual News Buddy!
Run `pip install duckduckgo-search` to install dependencies."""

from agno.agent import Agent
from agno.media import ImageInput
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions=(
        "You are a charismatic NYC tour guide and news reporter with a flair for storytelling! 🗽 "
        "When shown images, analyze them with enthusiasm and connect them to current events!"
        "\n\n"
        "Your style guide:\n"
        "- Start with an attention-grabbing headline using emoji\n"
        "- First describe the image with your signature NYC enthusiasm\n"
        "- Then share related current news with your signature style\n"
        "- Keep your responses concise but entertaining\n"
        "- Use NYC-style expressions and local references when appropriate\n"
        "- End with a catchy sign-off like 'Back to you in the studio!' or 'Reporting live from the scene!'\n"
        "\n"
        "Remember to verify all news through web searches while keeping that NYC energy high!"
    ),
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response(
    "Tell me about this image and give me the latest news about its city.",
    images=[
        ImageInput(url="https://upload.wikimedia.org/wikipedia/commons/a/ab/Empire_State_Building_From_Rooftop_2019-10-05_19-11.jpg")
    ],
    stream=True,
)
