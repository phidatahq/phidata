import json
import os
import time
from pydantic import BaseModel, Field
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
from phi.utils.log import logger

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class EvaluationJudge(BaseModel):
    """
    Represents a structured response from the evaluation judge on the generated response
    """

    criteria: str = Field(description="Criteria under which the answer falls bad, average or good")
    reasoning: str = Field(description="One liner reasoning behind choosing the respective criteria for answer")


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
        chunking_strategy=RecursiveChunking(),
    )

    qa_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="You are a helpful agent that can answer questions for a given question from the knowledge base.",
        instructions=[
            "Use the following pieces of retrieved context to answer the question.",
            "Your goal is to answer the user's question in detail.",
            "Provide a well-structured, clear, and concise answer.",
        ],
        knowledge=knowledge,
        search_knowledge=True,
    )

    judge_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="You are a judge evaluating the quality of generated answers.",
        instructions=[
            "Evaluate the quality of the given answer compared to the ground truth.",
            "Use the following criteria: bad, average, good.",
            "Provide a brief justification for the score.",
        ],
        response_model=EvaluationJudge,
    )

    def load_knowledge_base(self, recreate=False):
        """
        Loads the scraped and chunked content into the knowledge base.
        """
        logger.info("Loading knowledge base...")
        if self.qa_agent.knowledge is not None:
            self.qa_agent.knowledge.load(recreate=recreate)
        logger.info("Knowledge base loaded successfully.")

    def judge_answer(self, question, ground_truth, generated_answer):
        logger.info("Judging the generated answer...")
        prompt = f"""
        Question: {question}
        Ground Truth Answer: {ground_truth}
        Generated Answer: {generated_answer}

        Evaluate the quality of the Generated Answer compared to the Ground Truth Answer.
        Provide one of the following ratings: bad, average, good.
        Also, give a short justification for the rating.
        """
        judgment = self.judge_agent.run(prompt)
        return judgment.content

    def generate_answer(self, question):
        answer: RunResponse = RunResponse(content=None)
        answer = self.qa_agent.run(question)
        logger.info(f"Generating answer\n{answer.content}:\n")
        return answer

    def run(self, evaluation_path, output_path, knowledge_base_recreate=True):
        """
        Runs the workflow: scrapes the websites, chunks the content, stores it in the vector database,
        answers the given set of questions and judges them.
        Args:
            evaluation_path (str): The ground truth based on which quality of qa agent will be judged.
            output_path (str): Results will be saved here.
            knowledge_base_recreate: If set to True will recreate the Knowledge Base
        """

        load_start = time.time()
        self.load_knowledge_base(recreate=knowledge_base_recreate)
        load_end = time.time()
        duration_load = load_end - load_start
        logger.info(f"Loading of the website done in {duration_load:.2f} seconds")

        with open(evaluation_path, "r") as json_file:
            evaluation_data = json.load(json_file)

        results = []

        ans_start = time.time()
        # Running the qa_agent on the evaluation set
        for entry in evaluation_data:
            question = entry.get("Question")
            ground_truth = entry.get("Answer")
            # Generate Answer from the QA Agent
            logger.info(f"Asking question: {question}")
            generated_answer = self.generate_answer(question)
            # Judge the answer
            judgement = self.judge_answer(question, ground_truth, generated_answer)
            # Store the results
            results.append(
                {
                    "Question": question,
                    "Generated_Answer": generated_answer.content,
                    "Judgement": judgement.criteria,
                    "Reasoning": judgement.reasoning,
                }
            )

        ans_end = time.time()
        duration_ans = ans_end - ans_start
        logger.info(f"Answer generated in {duration_ans:.2f} seconds")

        # Write results to output CSV
        with open(output_path, "w") as json_file:
            json.dump(results, json_file, indent=4)

        logger.info(f"Evaluation results saved to {output_path}")

        response_content = {
            "results": results,
            "duration_load": duration_load,
            "duration_ans": duration_ans,
        }
        return RunResponse(content=response_content)


# Entry Point for the Workflow
if __name__ == "__main__":
    flow_start = time.time()

    evaluation_set_path = "qa_evaluation_set.json"  # Path to your evaluation set
    output_results_path = "evaluation_results.json"
    # Run the QA Workflow
    qa_workflow = QAWorkflow()
    qa_response = qa_workflow.run(evaluation_path=evaluation_set_path, output_path=output_results_path)
    logger.info(qa_response.content)

    flow_end = time.time()
    duration_flow = flow_end - flow_start
    logger.info(f"The question generation and evaluation workflow is completed in {duration_flow:.2f} seconds")
