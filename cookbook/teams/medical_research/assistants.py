from textwrap import dedent
from typing import List
from pathlib import Path

from pydantic import BaseModel, Field
from phi.assistant.team import Assistant
from phi.tools.arxiv_toolkit import ArxivToolkit

arxiv_toolkit = ArxivToolkit(download_dir=Path(__file__).parent.parent.parent.parent.joinpath("wip", "arxiv_pdfs"))


class SearchTerms(BaseModel):
    terms: List[str] = Field(..., description="List of 2 search terms related to a topic.")


class SearchResult(BaseModel):
    title: str = Field(..., description="Title of the article.")
    id: str = Field(..., description="The ID of the article.")
    summary: str = Field(..., description="Summary from the article.")
    pdf_url: str = Field(..., description="Url of the PDF from the article.")
    links: List[str] = Field(..., description="Links for the article.")
    reasoning: str = Field(..., description="Clear description of why you chose this article from the results.")


class SearchResults(BaseModel):
    results: List[SearchResult] = Field(..., description="List of top 3 search results.")


search_term_generator = Assistant(
    name="Medical Search Generator",
    description=dedent("""\
    You are a world-class medical researcher assigned a very important task.
    Given a topic, generate a list of 2 search terms for writing an article on that topic.
    These terms will be used to search the web for the most relevant articles on the topic.\
    """),
    output_model=SearchTerms,
    # debug_mode=True,
)

arxiv_search_assistant = Assistant(
    name="Arxiv Search Assistant",
    description=dedent("""\
    You are a world-class medical researcher assigned a very important task.
    Given a topic, search ArXiv for the top 10 articles about that topic and return the 3 most relevant articles to that topic.
    This is an important task and your output should be highly relevant to the original topic.\
    """),
    tools=[arxiv_toolkit],
    output_model=SearchResults,
    # debug_mode=True,
)

research_editor = Assistant(
    name="Medical Research Editor",
    description="You are a world-class medical researcher and your task is to generate a medical journal worthy report in the style of New York Times.",
    instructions=[
        "You will be provided with a topic and a list of articles along with their summary and content.",
        "Carefully read each articles and generate a medical journal worthy report in the style of New York Times.",
        "The report should be clear, concise, and informative.",
        "Focus on providing a high-level overview of the topic and the key findings from the articles.",
        "Do not copy the content from the articles, but use the information to generate a high-quality report.",
        "Do not include any personal opinions or biases in the report.",
    ],
    markdown=True,
    # debug_mode=True,
)
