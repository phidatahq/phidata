import json
import os
from pydantic import BaseModel, Field
from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.workflow import Workflow, RunEvent
from phi.utils.log import logger
from phi.tools.website import WebsiteTools
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def clean_content(text: str) -> str:
    """
    Clean invalid characters from the text to ensure proper encoding.
    Args:
        text (str): The text to clean.
    Returns:
        str: Cleaned text without invalid characters.
    """
    return text.encode("utf-8", errors="ignore").decode("utf-8")


def scrape_and_process(url: str) -> str:
    """
    Scrape content from a URL, remove duplicates, clean invalid characters,
    and return a single concatenated string of content.
    Args:
        url (str): The URL to scrape.
    Returns:
        str: The processed and concatenated content.
    """
    try:
        # Scrape content from the URL
        scraped_content = WebsiteTools().read_url(url)
        scraped_content = json.loads(scraped_content)
    except Exception as e:
        logger.error(f"Error scraping URL: {e}")
        return ""

    concatenated_content = []
    seen = set()

    # Process the scraped content
    for cont in scraped_content:
        try:
            content = cont.get('content')
            if content and content not in seen:
                concatenated_content.append(content)
                seen.add(content)
        except Exception:
            logger.warning("Failed to process content from scraped data.")
            continue

    # Clean and concatenate the content
    concatenated_content = [clean_content(content) for content in concatenated_content]
    return "\n--\n".join(concatenated_content)


url = "https://python.langchain.com/docs/how_to/sequence/#related"
concatenated_content = scrape_and_process(url)


class CodeSolution(BaseModel):
    """
    Represents a structured response containing prefix, imports, and code block.
    """
    prefix: str = Field(description="Description of the problem and approach")
    imports: str = Field(description="Code block import statements")
    code: str = Field(description="Code block not including import statements")


system_prompt = """
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


class CodeGenWorkflow(Workflow):
    """
    A workflow to generate, test, and validate code solutions using LCEL.
    """
    coding_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="A coding assistant that provides accurate and executable code solutions using LCEL, LangChain expression language.",
        system_message=system_prompt,
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

        Yields:
            RunResponse: Response containing the generated code solution.
        """
        attempt = 0
        error_message = ""
        generated_code = None

        while attempt < self.max_retries:
            logger.info(f"---ATTEMPT {attempt + 1}---")
            try:
                formatted_prompt = system_prompt.format(context=context, question=question)
                response = self.coding_agent.run(formatted_prompt)
                structured_response = response.content

                logger.info("---GENERATED CODE---")

                generated_code = structured_response

                logger.info("---CHECKING CODE---")
                result = self.check_code(structured_response)

                if result == "success":
                    yield RunResponse(
                        content=structured_response,
                        event=RunEvent.workflow_completed,
                    )
                    return

            except Exception as e:
                logger.error(f"---CODE BLOCK CHECK: FAILED IN ATTEMPT {attempt + 1}---")
                error_message = str(e)
                logger.error(f"Error: {error_message}")

            attempt += 1
            if attempt < self.max_retries:
                logger.info(f"---FIXING CODE (ATTEMPT {attempt + 1})---")
                generated_code = self.fix_code(
                    context=context,
                    question=question,
                    error_message=error_message,
                    generated_code=generated_code,
                )

        logger.error("---MAXIMUM ATTEMPTS REACHED: FAILED TO FIX CODE---")
        yield RunResponse(
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

    def fix_code(self, context: str, question: str, error_message: str, generated_code: CodeSolution) -> CodeSolution:
        """
        Fix the code by providing error context to the agent.

        Args:
            context (str): The context/documentation.
            question (str): User's question.
            error_message (str): Error message from the previous attempt.
            generated_code (CodeSolution): The previously generated code solution.

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
{generated_code.prefix}
{generated_code.imports}
{generated_code.code}

Answer with a description of the code solution, followed by the imports, and finally the functioning code block.
Ensure all imports are correct and the code is executable.
"""
        self.coding_agent.system_message = error_prompt
        response = self.coding_agent.run(error_prompt)
        return response.content


def check_import(solution) -> dict:
    """
    Check the validity of import statements in the generated code.

    Args:
        solution (CodeSolution): The generated code solution.

    Returns:
        dict: Dictionary containing import check results.
    """
    imports = solution.imports
    if not imports:
        return {"key": "import_check", "score": 0}
    try:
        exec(imports)
        return {"key": "import_check", "score": 1}
    except Exception:
        return {"key": "import_check", "score": 0}


def check_execution(solution) -> dict:
    """
    Check the execution of the code block in the generated solution.

    Args:
        solution (CodeSolution): The generated code solution.

    Returns:
        dict: Dictionary containing execution check results.
    """
    imports = solution.imports
    code = solution.code
    if not imports and not code:
        return {"key": "code_execution_check", "score": 0}
    try:
        exec(imports + "\n" + code)
        return {"key": "code_execution_check", "score": 1}
    except Exception:
        return {"key": "code_execution_check", "score": 0}


def evaluate_response(question, final_response):
    """
    Evaluate the response and return structured results.

    Args:
        question (str): The user's question.
        final_response (CodeSolution): The generated code solution.

    Returns:
        dict: Dictionary containing evaluation results.
    """
    import_check = check_import(final_response)
    execution_check = check_execution(final_response)

    result = {
        "question": question,
        "imports": final_response.imports,
        "code": final_response.code,
        "import_check": import_check["score"],
        "execution_check": execution_check["score"],
    }

    return result


if __name__ == "__main__":
    # The url to parse and use as context
    url = "https://python.langchain.com/docs/how_to/sequence/#related"
    question = "I'm invoking a LCEL chain with a map that contains the key 'input'. How do I transform the input?"

    concatenated_content = scrape_and_process(url)  # scrape the url and structure the data

    workflow = CodeGenWorkflow()
    responses = workflow.run(question=question, context=concatenated_content)

    final_content = None
    for response in responses:
        if response.event == RunEvent.workflow_completed:
            break
    final_content = response.content

    if final_content is None:
        logger.info(f"---NO RESPONSE GENERATED FOR QUESTION: {question}---")
        final_content = CodeSolution(prefix="", imports="", code="")

    result = evaluate_response(question, final_content)
    logger.info(result)
