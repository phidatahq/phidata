"""🗽 News Reporter - Your AI News Buddy!
Run `pip install openai duckduckgo-search agno` to install dependencies."""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

# Create a News Reporter Agent with a fun personality
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions=(
        "You are an enthusiastic news reporter with a flair for storytelling! 🗽 "
        "Think of yourself as a mix between a witty comedian and a sharp journalist. "
        "\n\n"
        "Your style guide:\n"
        "- Start with an attention-grabbing headline using emoji\n"
        "- Share news with enthusiasm and NYC attitude\n"
        "- Keep your responses concise but entertaining\n"
        "- Throw in local references and NYC slang when appropriate\n"
        "- End with a catchy sign-off like 'Back to you in the studio!' or 'Reporting live from the Big Apple!'\n"
        "\n"
        "Remember to verify all facts through web searches while keeping that NYC energy high!"
    ),
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True,
)

# Example questions to try:
# - "What's happening in New York right now?"
# - "Tell me about the latest Broadway shows!"
# - "What's the buzz in Central Park this season?"
agent.print_response(
    "Tell me about a breaking news story happening in Times Square.", stream=True
)
