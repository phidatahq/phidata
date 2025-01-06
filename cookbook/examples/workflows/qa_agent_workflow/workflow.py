import logging
import os
import time
from phi.run.response import RunResponse
from phi.workflow import Workflow
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.vectordb.lancedb import LanceDb
from phi.vectordb.search import SearchType
from phi.embedder.openai import OpenAIEmbedder
from phi.document.chunking.recursive import RecursiveChunking
from typing import List
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QAWorkflow(Workflow):
    """
    QA Workflow to scrape websites, chunk data, store it in a vector database, and answer a question.
    args: website_urls (list): List of website URLs to scrape and process.
    """
    website_urls: List = [
        "https://lilianweng.github.io/posts/2023-06-23-agent/",
        "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
        "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
    ]
    knowledge: WebsiteKnowledgeBase = WebsiteKnowledgeBase(
        urls=website_urls,
        max_links=10,
        vector_db=LanceDb(
            table_name="qa_agent_workflow",
            uri="/tmp/lancedb",
            search_type=SearchType.vector,
            embedder=OpenAIEmbedder(model="text-embedding-ada-002"),
        ),
        chunking_strategy=RecursiveChunking()
    )

    qa_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="You are a helpful assistant that can answer questions for a given question from the knowledge base.",
        instructions=[
            "Use the following pieces of retrieved context to answer the question.",
            "Your goal is to answer the user's question in detail.",
            "Provide a well-structured, clear, and concise answer.",
        ],
        knowledge=knowledge,
        search_knowledge=True,
        show_tool_calls=True,
        debug_mode=True,
    )

    def load_knowledge_base(self, recreate=False):
        """
        Loads the scraped and chunked content into the knowledge base.
        """
        logger.info("Loading knowledge base...")
        self.qa_agent.knowledge.load(recreate=recreate)
        logger.info("Knowledge base loaded successfully.")

    def generate_answer(self, question):
        answer: RunResponse = RunResponse(content=None)
        logger.info(f"Generating answer for {question}:\n")
        answer = self.qa_agent.run(question)
        return RunResponse(content=answer.content)

    def run(self, question, knowledge_base_recreate=True):
        """
        Runs the workflow: scrapes the websites, chunks the content, stores it in the vector database,
        and answers the given question.

        Args:
            question (str): The question to ask the QA Agent.
        """

        load_start = time.time()
        self.load_knowledge_base(recreate=knowledge_base_recreate)
        load_end = time.time()
        duration_load = load_end - load_start
        logger.info(f"Loading of the website done in {duration_load:.2f} seconds")
        # Generate Answer from the QA Agent
        logger.info(f"Asking question: {question}")
        ans_start = time.time()
        response = self.generate_answer(question)
        ans_end = time.time()
        duration_ans = ans_end - ans_start
        logger.info(f"Answer generated in {duration_ans:.2f} seconds")

        return response


# Entry Point for the Workflow
if __name__ == "__main__":
    flow_start = time.time()

    question = "How is the importance score of each word measured given a classifier?"
    # Run the QA Workflow
    qa_workflow = QAWorkflow()
    qa_response = qa_workflow.run(question=question, knowledge_base_recreate=False)
    print(qa_response.content)
    flow_end = time.time()
    duration_flow = flow_end - flow_start
    logger.info(f"The question generation workflow is completed in {duration_flow:.2f} seconds")

