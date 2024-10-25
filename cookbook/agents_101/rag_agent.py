"""Run `pip install openai lancedb tantivy` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.lancedb import LanceDb, SearchType
from pathlib import Path

def setup_knowledge_base(db_path="tmp/lancedb", load_data=False):
    knowledge_base = PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=LanceDb(
            table_name="recipes",
            uri=db_path,
            search_type=SearchType.vector
        )
    )
    
    if load_data:
        knowledge_base.load(upsert=True)
    
    return knowledge_base

def create_rag_agent(knowledge_base):
    return Agent(
        model=OpenAIChat(id="gpt-4o"),
        knowledge=knowledge_base,
        read_chat_history=True,
        show_tool_calls=True,
        markdown=True,
    )

if __name__ == "__main__":
    db_path = Path("tmp/lancedb")
    # İlk çalıştırmada True, sonraki çalıştırmalarda False yapın
    should_load_data = not db_path.exists()
    
    knowledge_base = setup_knowledge_base(str(db_path), should_load_data)
    agent = create_rag_agent(knowledge_base)
    agent.print_response("How do I make chicken and galangal in coconut milk soup", stream=True)
