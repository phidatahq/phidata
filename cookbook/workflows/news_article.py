"""
Please install dependencies using:
pip install openai duckduckgo-search newspaper4k lxml_html_clean phidata
"""

from shutil import rmtree
from pathlib import Path
from textwrap import dedent
from typing import Optional

from pydantic import BaseModel, Field
from phi.assistant import Assistant
from phi.workflow import Workflow, Task
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.newspaper4k import Newspaper4k


articles_dir = Path(__file__).parent.parent.parent.joinpath("wip", "articles")
if articles_dir.exists():
    rmtree(path=articles_dir, ignore_errors=True)
articles_dir.mkdir(parents=True, exist_ok=True)


class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")


researcher = Assistant(
    name="Article Researcher",
    tools=[DuckDuckGo()],
    description="Given a topic, search for 15 articles and return the 7 most relevant articles.",
    output_model=NewsArticle,
)

writer = Assistant(
    name="Article Writer",
    tools=[Newspaper4k()],
    description="You are a Senior NYT Editor and your task is to write a NYT cover story worthy article due tomorrow.",
    instructions=[
        "You will be provided with news articles and their links.",
        "Carefully read each article and think about the contents",
        "Then generate a final New York Times worthy article in the <article_format> provided below.",
        "Break the article into sections and provide key takeaways at the end.",
        "Make sure the title is catchy and engaging.",
        "Give the section relevant titles and provide details/facts/processes in each section."
        "Ignore articles that you cannot read or understand.",
        "REMEMBER: you are writing for the New York Times, so the quality of the article is important.",
    ],
    expected_output=dedent(
        """\
    An engaging, informative, and well-structured article in the following format:
    <article_format>
    ## Engaging Article Title

    ### Overview
    {give a brief introduction of the article and why the user should read this report}
    {make this section engaging and create a hook for the reader}

    ### Section 1
    {break the article into sections}
    {provide details/facts/processes in this section}

    ... more sections as necessary...

    ### Takeaways
    {provide key takeaways from the article}

    ### References
    - [Title](url)
    - [Title](url)
    - [Title](url)
    </article_format>
    """
    ),
)

news_article = Workflow(
    name="News Article Workflow",
    tasks=[
        Task(
            description="Find the 7 most relevant articles on a topic.",
            assistant=researcher,
            show_output=False,
        ),
        Task(
            description="Read each article and and write a NYT worthy news article.",
            assistant=writer,
        ),
    ],
    debug_mode=True,
    save_output_to_file="news_article.md",
)

news_article.print_response(
    "Hashicorp IBM acquisition",
    markdown=True,
)
