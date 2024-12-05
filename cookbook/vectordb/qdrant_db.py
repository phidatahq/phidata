# pip install phidata openai duckduckgo-search qdrant-client 
# pip install bs4 sqlalchemy
import os
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.vectordb.qdrant import Qdrant

from phi.agent import Agent
from phi.storage.agent.sqlite import SqlAgentStorage
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

# get Qdrant credentials from https://cloud.qdrant.io/
QDRANT_URL = "<endpoint-url>"
QDRANT_API_KEY = "<cluster-key>"
OPENAI_API_KEY = "<replace-with-your-key>" #platform.openai.com

os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

# vector database => COllection name or Index name
COLLECTION_NAME = "agentic-rag"

vector_db = Qdrant(
    collection=COLLECTION_NAME,
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

URL = ["https://qdrant.tech/documentation/overview/"] # knowledge source

knowledge_base = WebsiteKnowledgeBase(
    urls = URL,
    vector_db=vector_db, 
    max_links=10
)

knowledge_base.load() # index

agent = Agent(
    model = OpenAIChat(id="gpt-4o"),
    knowledge_base = knowledge_base, 
    storage = SqlAgentStorage(table_name="agentic-rag",db_file="qdrant_docs.db"),
    add_history_to_messages = True,
    tools = [DuckDuckGo()], 
    markdown=True,
    show_tool_calls=True,
)

query = "what is todays MSFT stock price?"
agent.print_response(query,stream=True)