import json
from phi.utils.log import logger
from phi.tools.website import WebsiteTools


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
        scraped_content_json = json.loads(scraped_content)
    except Exception as e:
        logger.error(f"Error scraping URL: {e}")
        return ""

    concatenated_content = []
    seen = set()

    # Process the scraped content
    for cont in scraped_content_json:
        try:
            content = cont.get("content")
            if content and content not in seen:
                concatenated_content.append(content)
                seen.add(content)
        except Exception:
            logger.warning("Failed to process content from scraped data.")
            continue

    # Clean and concatenate the content
    concatenated_content = [clean_content(content) for content in concatenated_content]
    return "\n--\n".join(concatenated_content)


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
        return {"key": "import_check", "score": "FAIL"}
    try:
        exec(imports)
        return {"key": "import_check", "score": "PASS"}
    except Exception:
        return {"key": "import_check", "score": "FAIL"}


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
        return {"key": "code_execution_check", "score": "FAIL"}
    try:
        exec(imports + "\n" + code)
        return {"key": "code_execution_check", "score": "PASS"}
    except Exception:
        return {"key": "code_execution_check", "score": "FAIL"}


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
