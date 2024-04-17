import json
from typing import List

from rich.pretty import pprint

from assistants import (
    SearchTerms,
    SearchResults,
    search_term_generator,
    arxiv_search_assistant,
    research_editor,
    arxiv_toolkit,
)

# Topic to generate a report on
topic = "AI in Healthcare"

# Generate a list of search terms
search_terms: SearchTerms = search_term_generator.run(topic)  # type: ignore
pprint(search_terms)

# Generate a list of search results
arxiv_search_results: List[SearchResults] = []
for search_term in search_terms.terms:
    search_results: SearchResults = arxiv_search_assistant.run(search_term)  # type: ignore
    arxiv_search_results.append(search_results)
# pprint(arxiv_search_results)

search_result_ids = []
for search_result in arxiv_search_results:
    search_result_ids.extend([result.id for result in search_result.results])

# Read the content of the search results
search_result_content = arxiv_toolkit.read_arxiv_papers(search_result_ids, pages_to_read=2)

research_editor.print_response(
    json.dumps({"topic": "AI in Healthcare", "articles": search_result_content}, indent=4), show_message=False
)
