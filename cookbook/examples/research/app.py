import json
from typing import Optional

import streamlit as st

from assistants import (
    SearchTerms,
    search_term_generator,
    arxiv_search_assistant,
    exa_search_assistant,
    research_editor,
    arxiv_toolkit,
)  # type: ignore


st.set_page_config(
    page_title="Research Team",
    page_icon=":orange_heart:",
)
st.title("AI Research Team")
st.markdown("##### :orange_heart: built by [phidata](https://github.com/phidatahq/phidata)")


def main() -> None:
    # Get topic for report
    input_topic = st.sidebar.text_input(
        ":female-scientist: Enter a topic",
        value="Language Agent Tree Search",
    )
    # Button to generate report
    generate_report = st.sidebar.button("Generate Report")
    if generate_report:
        st.session_state["topic"] = input_topic

    # Checkboxes for search
    st.sidebar.markdown("## Assistants")
    search_exa = st.sidebar.checkbox("Exa Search", value=True)
    search_arxiv = st.sidebar.checkbox("ArXiv Search", value=False)
    search_pubmed = st.sidebar.checkbox("PubMed Search", disabled=True)  # noqa
    search_google_scholar = st.sidebar.checkbox("Google Scholar Search", disabled=True)  # noqa
    use_cache = st.sidebar.toggle("Use Cache", value=False, disabled=True)  # noqa
    num_search_terms = st.sidebar.number_input(
        "Number of Search Terms", value=1, min_value=1, max_value=3, help="This will increase latency."
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Trending Topics")
    if st.sidebar.button("Language Agent Tree Search"):
        st.session_state["topic"] = "Language Agent Tree Search"

    if st.sidebar.button("AI in Healthcare"):
        st.session_state["topic"] = "AI in Healthcare"

    if st.sidebar.button("Acute respiratory distress syndrome"):
        st.session_state["topic"] = "Acute respiratory distress syndrome"

    if st.sidebar.button("Chromatic Homotopy Theory"):
        st.session_state["topic"] = "Chromatic Homotopy Theory"

    if "topic" in st.session_state:
        report_topic = st.session_state["topic"]

        search_terms: Optional[SearchTerms] = None
        with st.status("Generating Search Terms", expanded=True) as status:
            with st.container():
                search_terms_container = st.empty()
                search_generator_input = {"topic": report_topic, "num_terms": num_search_terms}
                search_terms = search_term_generator.run(json.dumps(search_generator_input))
                if search_terms:
                    search_terms_container.json(search_terms.model_dump())
            status.update(label="Search Terms Generated", state="complete", expanded=False)

        if not search_terms:
            st.write("Sorry report generation failed. Please try again.")
            return

        exa_content: Optional[str] = None
        arxiv_content: Optional[str] = None

        if search_exa:
            with st.status("Searching Exa", expanded=True) as status:
                with st.container():
                    exa_container = st.empty()
                    exa_search_results = exa_search_assistant.run(search_terms.model_dump_json(indent=4))
                    if exa_search_results and len(exa_search_results.results) > 0:
                        exa_content = exa_search_results.model_dump_json(indent=4)
                        exa_container.json(exa_search_results.results)
                status.update(label="Exa Search Complete Complete", state="complete", expanded=False)

        if search_arxiv:
            with st.status("Searching ArXiv (this takes a while)", expanded=True) as status:
                with st.container():
                    arxiv_container = st.empty()
                    arxiv_search_results = arxiv_search_assistant.run(search_terms.model_dump_json(indent=4))
                    if arxiv_search_results and len(arxiv_search_results.results) > 0:
                        arxiv_container.json(arxiv_search_results.results)
                status.update(label="ArXiv Search Complete", state="complete", expanded=False)

            if arxiv_search_results and len(arxiv_search_results) > 0:
                arxiv_paper_ids = []
                for search_result in arxiv_search_results:
                    arxiv_paper_ids.extend([result.id for result in search_result.results])

                if len(arxiv_paper_ids) > 0:
                    with st.status("Reading ArXiv Papers", expanded=True) as status:
                        with st.container():
                            arxiv_paper_ids_container = st.empty()
                            arxiv_content = arxiv_toolkit.read_arxiv_papers(arxiv_paper_ids, pages_to_read=2)
                            arxiv_paper_ids_container.json(arxiv_paper_ids)
                        status.update(label="Reading ArXiv Papers Complete", state="complete", expanded=False)

        report_input = ""
        report_input += f"# Topic: {report_topic}\n\n"
        report_input += "## Search Terms\n\n"
        report_input += f"{search_terms}\n\n"
        if arxiv_content:
            report_input += "## ArXiv Papers\n\n"
            report_input += "<arxiv_papers>\n\n"
            report_input += f"{arxiv_content}\n\n"
            report_input += "</arxiv_papers>\n\n"
        if exa_content:
            report_input += "## Web Search Content from Exa\n\n"
            report_input += "<exa_content>\n\n"
            report_input += f"{exa_content}\n\n"
            report_input += "</exa_content>\n\n"

        with st.spinner("Generating Report"):
            final_report = ""
            final_report_container = st.empty()
            for delta in research_editor.run(report_input):
                final_report += delta  # type: ignore
                final_report_container.markdown(final_report)

    st.sidebar.markdown("---")
    if st.sidebar.button("Restart"):
        st.rerun()


main()
