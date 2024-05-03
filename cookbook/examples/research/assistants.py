from textwrap import dedent
from typing import List
from pathlib import Path

from pydantic import BaseModel, Field
from phi.assistant.team import Assistant
from phi.tools.arxiv_toolkit import ArxivToolkit
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.exa import ExaTools

arxiv_toolkit = ArxivToolkit(download_dir=Path(__file__).parent.parent.parent.parent.joinpath("wip", "arxiv_pdfs"))


class SearchTerms(BaseModel):
    terms: List[str] = Field(..., description="List of 2 search terms related to a topic.")


class ArxivSearchResult(BaseModel):
    title: str = Field(..., description="Title of the article.")
    id: str = Field(..., description="The ID of the article.")
    summary: str = Field(..., description="Summary from the article.")
    pdf_url: str = Field(..., description="Url of the PDF from the article.")
    links: List[str] = Field(..., description="Links for the article.")
    reasoning: str = Field(..., description="Clear description of why you chose this article from the results.")


class ArxivSearchResults(BaseModel):
    results: List[ArxivSearchResult] = Field(..., description="List of top search results.")


class WebSearchResult(BaseModel):
    title: str = Field(..., description="Title of the article.")
    summary: str = Field(..., description="Summary from the article.")
    links: List[str] = Field(..., description="Links for the article.")
    reasoning: str = Field(..., description="Clear description of why you chose this article from the results.")


class WebSearchResults(BaseModel):
    results: List[WebSearchResult] = Field(..., description="List of top search results.")


search_term_generator = Assistant(
    name="Search Term Generator",
    description=dedent(
        """\
    You are a world-class researcher assigned a very important task.
    Given a topic, generate a list of 2 search terms that will be used to search the web for
    relevant articles regarding the topic.
    """
    ),
    add_datetime_to_instructions=True,
    output_model=SearchTerms,
    debug_mode=True,
)

arxiv_search_assistant = Assistant(
    name="Arxiv Search Assistant",
    description=dedent(
        """\
    You are a world-class researcher assigned a very important task.
    Given a topic, search ArXiv for the top 10 articles about that topic and return the 3 most relevant articles.
    This is an important task and your output should be highly relevant to the original topic.
    """
    ),
    tools=[arxiv_toolkit],
    output_model=ArxivSearchResults,
    # debug_mode=True,
)

exa_search_assistant = Assistant(
    name="Exa Search Assistant",
    description=dedent(
        """\
    You are a world-class researcher assigned a very important task.
    Given a topic, search Exa for the top 10 articles about that topic and return the 3 most relevant articles.
    You should return the article title, summary, and the content of the article.
    This is an important task and your output should be highly relevant to the original topic.
    """
    ),
    tools=[ExaTools()],
    output_model=WebSearchResults,
    # debug_mode=True,
)

ddg_search_assistant = Assistant(
    name="DuckDuckGo Search Assistant",
    description=dedent(
        """\
    You are a world-class researcher assigned a very important task.
    Given a topic, search duckduckgo for the top 10 articles about that topic and return the 3 most relevant articles.
    You should return the article title, summary, and the content of the article.
    This is an important task and your output should be highly relevant to the original topic.
    """
    ),
    tools=[DuckDuckGo()],
    output_model=WebSearchResults,
    # debug_mode=True,
)

research_editor = Assistant(
    name="Research Editor",
    description="You are a world-class researcher and your task is to generate a NYT cover story worthy research report.",
    instructions=[
        "You will be provided with a topic and a list of articles along with their summary and content.",
        "Carefully read each articles and generate a NYT worthy report that can be published as the cover story.",
        "Focus on providing a high-level overview of the topic and the key findings from the articles.",
        "Do not copy the content from the articles, but use the information to generate a high-quality report.",
        "Do not include any personal opinions or biases in the report.",
    ],
    markdown=True,
    # debug_mode=True,
)
