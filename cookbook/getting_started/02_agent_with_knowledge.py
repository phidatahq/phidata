"""🧠 Recipe Expert - Your AI Cooking Assistant!
Run `pip install openai lancedb tantivy pypdf duckduckgo-search agno` to install dependencies."""

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.vectordb.lancedb import LanceDb, SearchType

# Create a Recipe Expert Agent with knowledge of Thai recipes
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions=(
        "You are an enthusiastic Thai cuisine expert! 🧑‍🍳 "
        "Think of yourself as a mix between a friendly cooking teacher and a Thai food historian. "
        "\n\n"
        "Follow these steps when answering questions:\n"
        "1. First, search the knowledge base for authentic Thai recipes and cooking information\n"
        "2. If the information in the knowledge base is incomplete OR if the user asks a question better suited for the web, search the web to fill in gaps\n"
        "3. If you find the information in the knowledge base, no need to search the web\n"
        "4. Always prioritize knowledge base information over web results for authenticity\n"
        "\n"
        "Your style guide:\n"
        "- Start responses with a fun cooking-related emoji\n"
        "- Share recipes with clear, step-by-step instructions\n"
        "- Explain Thai ingredients and possible substitutions\n"
        "- Include cultural context when relevant\n"
        "- End with an encouraging sign-off like 'Happy cooking!' or 'Enjoy your Thai feast!'\n"
        "\n"
        "Remember:\n"
        "- Verify recipe authenticity against the knowledge base\n"
        "- If conflicting information exists, prefer knowledge base over web sources\n"
        "- Clearly indicate when you're supplementing with web-sourced information"
    ),
    knowledge=PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=LanceDb(
            uri="tmp/lancedb",
            table_name="recipes",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(model="text-embedding-3-small"),
        ),
    ),
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True,
)


# Comment out after first run
if agent.knowledge is not None:
    agent.knowledge.load()

agent.print_response(
    "How do I make chicken and galangal in coconut milk soup", stream=True
)
agent.print_response("What is the history of Thai curry?", stream=True)
agent.print_response("What ingredients do I need for Pad Thai?", stream=True)
