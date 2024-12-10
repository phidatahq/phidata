from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
import os
#os.environ["OPENAI_API_KEY"] = ""
from phi.vectordb.mongodb import MDBVector
db_url = ""
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=MDBVector(collection_name="recipes", db_url=db_url, wait_until_index_ready=60, wait_after_insert=300),
) #adjust wait_after_insert and wait_until_index_ready to your needs
knowledge_base.load(recreate=True)  
agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("How to make Thai curry?", markdown=True)
# Lets try with recreate=False
knowledge_base.load(recreate=False)  
agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("How to make Thai curry?", markdown=True)