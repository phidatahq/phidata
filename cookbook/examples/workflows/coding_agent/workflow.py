import os
from dotenv import load_dotenv

from pydantic import BaseModel, Field

from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.workflow import Workflow, RunEvent
from phi.utils.log import logger
from cookbook.examples.workflows.coding_agent.utils import scrape_and_process, evaluate_response

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class CodeSolution(BaseModel):
    """
    Represents a structured response containing prefix, imports, and code block.
    """

    prefix: str = Field(description="Description of the problem and approach")
    imports: str = Field(description="Code block import statements")
    code: str = Field(description="Code block not including import statements")


class CodeGenWorkflow(Workflow):
    """
    A workflow to generate, test, and validate code solutions using LCEL.
    """

    system_prompt: str = """
    You are a coding assistant with expertise in LCEL, LangChain expression language.

    Here is the LCEL documentation:
    -------
    {context}
    -------
    Answer the user question based on the above provided documentation.
    Ensure any code you provide can be executed with all required imports and variables defined.
    Structure your answer:
    1) A prefix describing the code solution.
    2) The import statements.
    3) The functioning code block.

    User question:
    {question}
    """

    coding_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="A coding assistant that provides accurate and executable code solutions using LCEL, LangChain expression language.",
        system_prompt=system_prompt,
        response_model=CodeSolution,
        structured_outputs=True,
    )
    max_retries: int = 3

    def run(self, question: str, context: str):
        """
        Run the workflow to generate a code solution for the given question and context.

        Args:
            question (str): User's question.
            context (str): Contextual information/documentation.

        Return:
            RunResponse: Response containing the generated code solution.
        """
        attempt = 0
        error_message = ""
        generated_code = None

        while attempt < self.max_retries:
            logger.info(f"---ATTEMPT {attempt + 1}---")
            try:
                if attempt == 0:
                    # First attempt: Generate initial code
                    formatted_prompt = self.system_prompt.format(context=context, question=question)
                    response = self.coding_agent.run(formatted_prompt, stream=False)
                    logger.info("---GENERATED CODE---")
                    generated_code = response.content
                else:
                    # Subsequent attempts: Fix the code
                    logger.info(f"---FIXING CODE (ATTEMPT {attempt + 1})---")
                    fixed_code = self.fix_code(
                        context=context,
                        question=question,
                        error_message=error_message,
                        previous_code=generated_code,  # type: ignore
                    )
                    generated_code = fixed_code

                # Check the generated or fixed code
                logger.info("---CHECKING CODE---")
                result = self.check_code(generated_code)  # type: ignore

                if result == "success":
                    logger.info("---CODE CHECK SUCCESSFUL---")
                    return RunResponse(
                        content=generated_code,
                        event=RunEvent.workflow_completed,
                    )

            except Exception as e:
                logger.error(f"---CODE BLOCK CHECK: FAILED IN ATTEMPT {attempt + 1}---")
                error_message = str(e)
                logger.error(f"Error: {error_message}")

            # Increment attempt counter
            attempt += 1

            # If all attempts fail
        logger.error("---MAXIMUM ATTEMPTS REACHED: FAILED TO FIX CODE---")
        return RunResponse(
            content=generated_code,
        )

    def check_code(self, code_solution: CodeSolution) -> str:
        """
        Check if the provided code solution executes without errors.

        Args:
            code_solution (CodeSolution): The generated code solution.

        Returns:
            str: "success" if the code passes all checks, "failed" otherwise.
        """
        try:
            exec(code_solution.imports)
            logger.info("---CODE IMPORT CHECK: PASSED---")
        except Exception as e:
            logger.error("---CODE IMPORT CHECK: FAILED---")
            logger.error(f"Error: {str(e)}")
            return "failed"

        try:
            exec(f"{code_solution.imports}\n{code_solution.code}")
            logger.info("---CODE EXECUTION CHECK: PASSED---")
        except Exception as e:
            logger.error("---CODE EXECUTION CHECK: FAILED---")
            logger.error(f"Error: {str(e)}")
            return "failed"

        logger.info("---NO CODE TEST FAILURES---")
        return "success"

    def fix_code(self, context: str, question: str, error_message: str, previous_code: CodeSolution) -> CodeSolution:
        """
        Fix the code by providing error context to the agent.

        Args:
            context (str): The context/documentation.
            question (str): User's question.
            error_message (str): Error message from the previous attempt.
            previous_code (CodeSolution): The previously generated code solution.

        Returns:
            CodeSolution: The fixed code solution.
        """
        error_prompt = f"""
        You are a coding assistant with expertise in LCEL, LangChain expression language.
        Here is a full set of LCEL documentation:
        -------
        {context}
        -------
        The previous code attempt failed with the following error:
        {error_message}

        Your coding task:
        {question}

        Previous code attempt:
        {previous_code.prefix}
        {previous_code.imports}
        {previous_code.code}

        Answer with a description of the code solution, followed by the imports, and finally the functioning code block.
        Ensure all imports are correct and the code is executable.
        """
        self.coding_agent.system_prompt = error_prompt
        response: RunResponse = self.coding_agent.run(error_prompt)
        solution: CodeSolution = response.content  # type: ignore
        return solution


if __name__ == "__main__":
    # The url to parse and use as context
    url = "https://python.langchain.com/docs/how_to/sequence/#related"
    question = "How to structure output of an LCEL chain as a JSON object?"

    concatenated_content = scrape_and_process(url)  # Scrape the URL and structure the data
    workflow = CodeGenWorkflow()
    final_content = workflow.run(question=question, context=concatenated_content)

    if final_content is None:
        logger.info(f"---NO RESPONSE GENERATED FOR QUESTION: {question}---")
        final_content = RunResponse(
            content=CodeSolution(prefix="", imports="", code=""),
        )

    result = evaluate_response(question, final_content.content)
    logger.info(result)
