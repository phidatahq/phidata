from textwrap import dedent

from phi.assistant import Assistant
from phi.embedder.openai import OpenAIEmbedder
from phi.llm.openai import OpenAIChat
from phi.memory import AssistantMemory
from phi.memory.db.postgres import PgMemoryDb
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.tools.exa import ExaTools
from phi.vectordb.pgvector import PgVector2

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

assistant = Assistant(
    # LLM to use for the Assistant
    llm=OpenAIChat(model="gpt-4o"),
    # Add personalization to the assistant by creating memories
    create_memories=True,
    # Store the memories in a database
    memory=AssistantMemory(db=PgMemoryDb(table_name="assistant_memory", db_url=db_url)),
    # Store runs in a database
    storage=PgAssistantStorage(table_name="assistant_storage", db_url=db_url),
    # Store knowledge in a vector database
    knowledge_base=WebsiteKnowledgeBase(
        urls=["https://blog.samaltman.com/gpt-4o"],
        max_links=3,
        vector_db=PgVector2(
            db_url=db_url,
            collection="assistant_knowledge",
            embedder=OpenAIEmbedder(model="text-embedding-3-small", dimensions=1536),
        ),
        # 3 references are added to the prompt
        num_documents=3,
    ),
    tools=[ExaTools()],
    description="You are an NYT reporter writing a cover story on a topic",
    instructions=[
        "Always search your knowledge base first for information on the topic.",
        "Then use exa to search for more information.",
        "Break the article into sections and provide key takeaways at the end.",
        "Make sure the title is catchy and engaging.",
        "Give the section relevant titles and provide details/facts/processes in each section.",
    ],
    expected_output=dedent(
        """\
    An engaging, informative, and well-structured article in the following format:
    <article_format>
    ## Engaging Article Title

    ### Overview
    {give a brief introduction of the article and why the user should read this report}
    {make this section engaging and create a hook for the reader}

    ### Section 1
    {break the article into sections}
    {provide details/facts/processes in this section}

    ... more sections as necessary...

    ### Takeaways
    {provide key takeaways from the article}

    ### References
    - [Title](url)
    - [Title](url)
    - [Title](url)

    ### Author
    {Author Name}, {date}
    </article_format>
    """
    ),
    # This setting adds a tool to search the knowledge base for information
    search_knowledge=True,
    # This setting adds a tool to get chat history
    read_chat_history=True,
    # This setting tells the LLM to format messages in markdown
    markdown=True,
    # This setting adds chat history to the messages
    add_chat_history_to_messages=True,
    # This setting adds 6 previous messages from chat history to the messages sent to the LLM
    num_history_messages=6,
    # This setting adds the current datetime to the instructions
    add_datetime_to_instructions=True,
    show_tool_calls=True,
    # debug_mode=True,
)

if assistant.knowledge_base:
    assistant.knowledge_base.load()

assistant.print_response("My name is John and I am an NYT reporter writing a cover story on a topic.")
assistant.print_response("Write an article on GPT-4o")
