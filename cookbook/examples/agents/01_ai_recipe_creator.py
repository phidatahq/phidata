from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://www.poshantracker.in/pdf/Awareness/MilletsRecipeBook2023_Low%20Res_V5.pdf", "https://www.cardiff.ac.uk/__data/assets/pdf_file/0003/123681/Recipe-Book.pdf"],
    vector_db=PgVector(table_name="recipes", db_url=db_url),
)
knowledge_base.load(recreate=False)

recipe_agent = Agent(
    name="RecipeGenie",
    knowledge_base=knowledge_base,
    search_knowledge=True,
    instructions=["Search for recipes based on the ingredients and time available from the knowledge base.",
                  "Additionally, include the nutritional information and cooking instructions for the recommended recipes.",
                  "You can alternatively search Youtube for video links related to the recommended recipes (as given from the knowledge base) from famous chefs with most subscribers and include them in the response."],
)

recipe_agent.print_response("I have milk and butter, please suggest me a recipe with 500g protein", markdown=True)
