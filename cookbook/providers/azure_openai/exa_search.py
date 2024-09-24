import os

from dotenv import load_dotenv

from phi.agent import Agent
from phi.model.azure import AzureOpenAIChat
from phi.tools.exa import ExaTools
from phi.tools.website import WebsiteTools

load_dotenv()

azure_model = AzureOpenAIChat(
    model=os.getenv("AZURE_OPENAI_MODEL_NAME"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
)

agent = Agent(
    model=azure_model, tools=[ExaTools(), WebsiteTools()], show_tool_calls=True
)

agent.print_response(
    "Produce this table: research chromatic homotopy theory."
    "Access each link in the result outputting the summary for that article, its link, and keywords; "
    "After the table output make conceptual ascii art of the overarching themes and constructions",
    markdown=True,
)
