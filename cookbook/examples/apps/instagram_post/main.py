from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.exa import ExaTools
from agno.tools.dalle import DalleTools
from agno.tools.browserless import BrowserlessTools


competitor_research_agent = Agent(
    name="competitor_research_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[BrowserlessTools(), ExaTools()],
    role="""You are a competitor research agent. You are given a list of competitors and you need to research them
    You'll return insights about the competitors and market to help the creative content agent to write a post and image_generation_agent to generate an image.
    """,
    markdown=True,
    show_tool_calls=True,
)

creative_content_agent = Agent(
    name="creative_content_agent",
    model=OpenAIChat(id="o3-mini"),
    tools=[ExaTools()],
    role="""You are a creative content agent. You'll get insights about the competitors and market to help you create a post. Write a post that is engaging and interesting.
    """,
    markdown=True,
    show_tool_calls=True,
)

image_generation_agent = Agent(
    name="image_generation_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[DalleTools()],
    role="""You are an image generation agent. You'll get insights about the competitors and market to help you create an image.
    """,
    markdown=True,
    show_tool_calls=True,
)

content_direction_agent = Agent(
    name="content_direction_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    role="""You are a content direction agent. You'll have to create an engaging and interesting post with help of your team competitor_research_agent , creative_content_agent and image_generation_agent.
    """,
    team=[competitor_research_agent, creative_content_agent, image_generation_agent],
    markdown=True,
    show_tool_calls=True,
)

content_direction_agent.print_response(
    "My product is ai agent called agno.com. I want to create a post about it. Can you research the market and competitors?"
)

