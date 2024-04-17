from typing import List

from rich.pretty import pprint

from assistants import (
    SearchTerms,
    ArxivSearchResults,
    search_term_generator,
    arxiv_search_assistant,
    exa_search_assistant,
    research_editor,
    arxiv_toolkit,
)  # noqa

# Topic to generate a report on
topic = "Latest AI in Healthcare Research"

# Generate a list of search terms
search_terms: SearchTerms = search_term_generator.run(topic)  # type: ignore
pprint(search_terms)

# Generate a list of search results
arxiv_search_results: List[ArxivSearchResults] = []
for search_term in search_terms.terms:
    search_results: ArxivSearchResults = arxiv_search_assistant.run(search_term)  # type: ignore
    arxiv_search_results.append(search_results)
# pprint(arxiv_search_results)

search_result_ids = []
for search_result in arxiv_search_results:
    search_result_ids.extend([result.id for result in search_result.results])

# Read ArXiv papers
arxiv_content = arxiv_toolkit.read_arxiv_papers(search_result_ids, pages_to_read=2)

# Get web content
web_content = exa_search_assistant.run(search_terms.model_dump_json())  # type: ignore

report_input = ""
report_input += f"# Topic: {topic}\n\n"
report_input += "## Search Terms\n\n"
report_input += f"{search_terms}\n\n"
if arxiv_content:
    report_input += "## ArXiv Papers\n\n"
    report_input += "<arxiv_papers>\n\n"
    report_input += f"{arxiv_content}\n\n"
    report_input += "</arxiv_papers>\n\n"
if web_content:
    report_input += "## Web Content\n\n"
    report_input += "<web_content>\n\n"
    report_input += f"{web_content}\n\n"
    report_input += "</web_content>\n\n"

pprint(report_input)
# Generate a report
research_editor.print_response(report_input, show_message=False)
