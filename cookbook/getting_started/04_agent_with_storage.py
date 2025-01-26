"""🧠 Recipe Expert with Storage - Your AI Thai Cooking Assistant!

This example shows how to create an AI cooking assistant that combines knowledge from a
curated recipe database with web searching capabilities. The agent uses a PDF knowledge base
of authentic Thai recipes and can supplement this information with web searches when needed.

Example prompts to try:
- "How do I make authentic Pad Thai?"
- "What's the difference between red and green curry?"
- "Can you explain what galangal is and possible substitutes?"
- "Tell me about the history of Tom Yum soup"
- "What are essential ingredients for a Thai pantry?"
- "How do I make Thai basil chicken (Pad Kra Pao)?"

Run `pip install openai lancedb tantivy pypdf duckduckgo-search sqlalchemy agno` to install dependencies.
"""

from typing import List, Optional

import typer
from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.models.openai import OpenAIChat
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.vectordb.lancedb import LanceDb, SearchType
from rich import print

agent_knowledge = PDFUrlKnowledgeBase(
    urls=["https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="recipe_knowledge",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)
# Comment out after the knowledge base is loaded
# if agent_knowledge is not None:
#     agent_knowledge.load()

agent_storage = SqliteAgentStorage(table_name="recipe_agent", db_file="tmp/agents.db")


def recipe_agent(user: str = "user"):
    session_id: Optional[str] = None

    # Ask the user if they want to start a new session or continue an existing one
    new = typer.confirm("Do you want to start a new session?")

    if not new:
        existing_sessions: List[str] = agent_storage.get_all_session_ids(user)
        if len(existing_sessions) > 0:
            session_id = existing_sessions[0]

    agent = Agent(
        user_id=user,
        session_id=session_id,
        model=OpenAIChat(id="gpt-4o"),
        instructions=(
            "You are a passionate and knowledgeable Thai cuisine expert! 🧑‍🍳\n"
            "Think of yourself as a combination of a warm, encouraging cooking instructor, "
            "a Thai food historian, and a cultural ambassador.\n"
            "\n"
            "Follow these steps when answering questions:\n"
            "1. First, search the knowledge base for authentic Thai recipes and cooking information\n"
            "2. If the information in the knowledge base is incomplete OR if the user asks a question better suited for the web, search the web to fill in gaps\n"
            "3. If you find the information in the knowledge base, no need to search the web\n"
            "4. Always prioritize knowledge base information over web results for authenticity\n"
            "5. If needed, supplement with web searches for:\n"
            "   - Modern adaptations or ingredient substitutions\n"
            "   - Cultural context and historical background\n"
            "   - Additional cooking tips and troubleshooting\n"
            "\n"
            "Communication style:\n"
            "1. Start each response with a relevant cooking emoji\n"
            "2. Structure your responses clearly:\n"
            "   - Brief introduction or context\n"
            "   - Main content (recipe, explanation, or history)\n"
            "   - Pro tips or cultural insights\n"
            "   - Encouraging conclusion\n"
            "3. For recipes, include:\n"
            "   - List of ingredients with possible substitutions\n"
            "   - Clear, numbered cooking steps\n"
            "   - Tips for success and common pitfalls\n"
            "4. Use friendly, encouraging language\n"
            "\n"
            "Special features:\n"
            "- Explain unfamiliar Thai ingredients and suggest alternatives\n"
            "- Share relevant cultural context and traditions\n"
            "- Provide tips for adapting recipes to different dietary needs\n"
            "- Include serving suggestions and accompaniments\n"
            "\n"
            "End each response with an uplifting sign-off like:\n"
            "- 'Happy cooking! ขอให้อร่อย (Enjoy your meal)!'\n"
            "- 'May your Thai cooking adventure bring joy!'\n"
            "- 'Enjoy your homemade Thai feast!'\n"
            "\n"
            "Remember:\n"
            "- Always verify recipe authenticity with the knowledge base\n"
            "- Clearly indicate when information comes from web sources\n"
            "- Be encouraging and supportive of home cooks at all skill levels"
        ),
        storage=agent_storage,
        knowledge=agent_knowledge,
        tools=[DuckDuckGoTools()],
        # Show tool calls in the response
        show_tool_calls=True,
        # To provide the agent with the chat history
        # We can either:
        # 1. Provide the agent with a tool to read the chat history
        # 2. Automatically add the chat history to the messages sent to the model
        #
        # 1. Provide the agent with a tool to read the chat history
        read_chat_history=True,
        # 2. Automatically add the chat history to the messages sent to the model
        # add_history_to_messages=True,
        # Number of historical responses to add to the messages.
        # num_history_responses=3,
        markdown=True,
    )

    print("You are about to chat with an agent!")
    if session_id is None:
        session_id = agent.session_id
        if session_id is not None:
            print(f"Started Session: {session_id}\n")
        else:
            print("Started Session\n")
    else:
        print(f"Continuing Session: {session_id}\n")

    # Runs the agent as a command line application
    agent.cli_app(markdown=True)


if __name__ == "__main__":
    typer.run(recipe_agent)
