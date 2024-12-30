import logging
from phi.run.response import RunResponse
from phi.workflow import Workflow
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.vectordb.lancedb import LanceDb
from phi.vectordb.search import SearchType
from phi.embedder.openai import OpenAIEmbedder
from phi.document.chunking.recursive import RecursiveChunking
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QAWorkflow(Workflow):
    """
    QA Workflow to scrape websites, chunk data, store it in a vector database, and answer a question.
    args: website_urls (list): List of website URLs to scrape and process.
    """
    def __init__(self, website_urls, **data):
        super().__init__(**data)
        self.website_urls = website_urls

        self.qa_agent: Agent = Agent(
            model=OpenAIChat(id="gpt-4o"),
            description="You are a helpful assistant that can answer questions for a given question from the knowledge base.",
            instructions=[
                "Use the following pieces of retrieved context to answer the question.",
                "Your goal is to answer the user's question in detail.",
                "Provide a well-structured, clear, and concise answer.",
            ],
            knowledge=WebsiteKnowledgeBase(
                urls=self.website_urls,  # Use instance-specific attribute
                max_links=10,  # Follow up to 10 links from each website
                vector_db=LanceDb(
                    table_name="qa_agent_workflow",
                    uri="/tmp/lancedb2",
                    search_type=SearchType.vector,
                    embedder=OpenAIEmbedder(model="text-embedding-ada-002"),
                ),
                chunking_strategy=RecursiveChunking()
            ),
            search_knowledge=True,
            show_tool_calls=True,
            debug_mode=True,
        )

    def load_knowledge_base(self, recreate=False):
        """
        Loads the scraped and chunked content into the knowledge base.
        """
        logger.info("Loading knowledge base...")
        self.qa_agent.knowledge_base.load(recreate=recreate)
        logger.info("Knowledge base loaded successfully.")

    def generate_answer(self, question):
        answer: RunResponse = RunResponse(content=None)
        logger.info(f"Generating answer for {question}:\n")
        answer = self.qa_agent.run(question)
        return answer.content

    def run(self, question):
        """
        Runs the workflow: scrapes the websites, chunks the content, stores it in the vector database,
        and answers the given question.

        Args:
            question (str): The question to ask the QA Agent.
        """

        self.load_knowledge_base(recreate=True)
        # Generate Answer from the QA Agent
        logger.info(f"Asking question: {question}")
        response = self.generate_answer(question)

        return response


# Entry Point for the Workflow
if __name__ == "__main__":
    website_urls = [
        "https://lilianweng.github.io/posts/2023-06-23-agent/",
        "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
        "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
    ]

    question = "What does Lilian Weng say about the types of agent memory?"

    # Run the QA Workflow
    qa_workflow = QAWorkflow(website_urls)
    qa_workflow.run(question)
