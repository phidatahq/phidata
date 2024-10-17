from typing import Optional

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.knowledge.agent import AgentKnowledge
from phi.storage.agent.postgres import PgAgentStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.vectordb.pgvector import PgVector, SearchType

from agents.settings import agent_settings
from db.session import db_url

example_agent_storage = PgAgentStorage(table_name="example_agent_sessions", db_url=db_url)
example_agent_knowledge = AgentKnowledge(
    vector_db=PgVector(table_name="example_agent_knowledge", db_url=db_url, search_type=SearchType.hybrid)
)


def get_example_agent(
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Agent:
    return Agent(
        name="Example Agent",
        agent_id="example-agent",
        session_id=session_id,
        user_id=user_id,
        # The model to use for the agent
        model=OpenAIChat(
            id=model_id or agent_settings.gpt_4,
            max_tokens=agent_settings.default_max_completion_tokens,
            temperature=agent_settings.default_temperature,
        ),
        # Tools available to the agent
        tools=[DuckDuckGo()],
        # A description of the agent that guides its overall behavior
        description="You are a highly advanced AI agent with access to an extensive knowledge base and powerful web-search capabilities.",
        # A list of instructions to follow, each as a separate item in the list
        instructions=[
            "Always search your knowledge base first.\n"
            "  - Search your knowledge base before seeking external information.\n"
            "  - Provide answers based on your existing knowledge whenever possible.",
            "Then search the web if no information is found in your knowledge base.\n"
            "  - If the information is not available in your knowledge base, use `duckduckgo_search` to find relevant information.",
            "Provide concise and relevant answers.\n"
            "  - Keep your responses brief and to the point.\n"
            "  - Focus on delivering the most pertinent information without unnecessary detail.",
            "Ask clarifying questions.\n"
            "  - If a user's request is unclear or incomplete, ask specific questions to obtain the necessary details.\n"
            "  - Ensure you fully understand the inquiry before formulating a response.",
            "Verify the information you provide for accuracy.",
            "Cite reliable sources when referencing external data.",
        ],
        # Format responses as markdown
        markdown=True,
        # Show tool calls in the response
        show_tool_calls=True,
        # Add the current date and time to the instructions
        add_datetime_to_instructions=True,
        # Store agent sessions in the database
        storage=example_agent_storage,
        # Enable read the chat history from the database
        read_chat_history=True,
        # Store knowledge in a vector database
        knowledge=example_agent_knowledge,
        # Enable searching the knowledge base
        search_knowledge=True,
        # Enable monitoring on phidata.app
        monitoring=True,
        # Show debug logs
        debug_mode=debug_mode,
    )
