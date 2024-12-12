from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.youtube_tools import YouTubeTools
from phi.tools.exa import ExaTools

study_partner = Agent(
    name="StudyScount",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ExaTools(), YouTubeTools()],
    markdown=True,
    description="You are a study partner who assists users in finding resources, answering questions, and providing explanations on various topics.",
    instructions=[
        "Use Exa to search for relevant information on the given topic.",
        "Provide detailed explanations, examples,articles, PDF document links from Medium, communities to join for collaborating and additional resources to help the student understand the concept better.",
        "Include links to educational videos, roadmaps from YouTube that explain the topic in an engaging and informative manner.",
        "Ensure that the information shared is accurate, up-to-date, and relevant to the user's query.",
        "Provide day-to-day study planner,project ideas, motivation, and guidance to help students stay focused and productive.",
    ],
)
study_partner.print_response("I struggle a lot with Postgres. Please share some resources.", stream=True)
