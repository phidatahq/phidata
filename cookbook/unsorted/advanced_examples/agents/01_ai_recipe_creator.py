from agno.agent import Agent
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.tools.exa import ExaTools
from agno.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=[
        "https://www.cardiff.ac.uk/__data/assets/pdf_file/0003/123681/Recipe-Book.pdf",
    ],
    vector_db=PgVector(table_name="recipes", db_url=db_url),
)
knowledge_base.load(recreate=False)

recipe_agent = Agent(
    name="RecipeGenie",
    knowledge=knowledge_base,
    search_knowledge=True,
    tools=[ExaTools()],
    markdown=True,
    instructions=[
        "Search for recipes based on the ingredients and time available from the knowledge base.",
        "Include the exact calories, preparation time, cooking instructions, and highlight allergens for the recommended recipes.",
        "Always search exa for recipe links or tips related to the recipes apart from knowledge base.",
        "Provide a list of recipes that match the user's requirements and preferences.",
    ],
)

recipe_agent.print_response(
    "I have potatoes, tomatoes, onions, garlic, ginger, and chicken. Suggest me a quick recipe for dinner",
    stream=True,
)
