# Inspired by: https://github.com/anthropics/anthropic-cookbook/blob/main/misc/prompt_caching.ipynb
import requests
from bs4 import BeautifulSoup

from phi.assistant import Assistant
from phi.llm.anthropic import Claude


def fetch_article_content(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    # Get text
    text = soup.get_text()
    # Break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    text = "\n".join(chunk for chunk in chunks if chunk)
    return text


# Fetch the content of the article
book_url = "https://www.gutenberg.org/cache/epub/1342/pg1342.txt"
book_content = fetch_article_content(book_url)

print(f"Fetched {len(book_content)} characters from the book.")

assistant = Assistant(
    llm=Claude(
        model="claude-3-5-sonnet-20240620",
        cache_system_prompt=True,
    ),
    system_prompt=book_content[:10000],
    debug_mode=True,
)
assistant.print_response("Give me a one line summary of this book", markdown=True, stream=True)
print("Prompt cache creation tokens: ", assistant.llm.metrics["cache_creation_tokens"])  # type: ignore
print("Prompt cache read tokens: ", assistant.llm.metrics["cache_read_tokens"])  # type: ignore

# assistant.print_response("Give me a one line summary of this book", markdown=True, stream=False)
# print("Prompt cache creation tokens: ", assistant.llm.metrics["cache_creation_tokens"])
# print("Prompt cache read tokens: ", assistant.llm.metrics["cache_read_tokens"])
