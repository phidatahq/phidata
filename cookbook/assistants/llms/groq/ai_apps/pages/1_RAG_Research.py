import json
from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.document import Document
from phi.tools.tavily import TavilyTools
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.utils.log import logger

from assistants import get_rag_research_assistant  # type: ignore

st.set_page_config(
    page_title="RAG Research Assistant",
    page_icon=":orange_heart:",
)
st.title("RAG Research Assistant")
st.markdown("##### :orange_heart: Built using [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["research_assistant"] = None
    st.session_state["research_assistant_run_id"] = None
    if "url_scrape_key" in st.session_state:
        st.session_state["url_scrape_key"] += 1
    if "file_uploader_key" in st.session_state:
        st.session_state["file_uploader_key"] += 1
    st.rerun()


def main() -> None:
    # Get LLM Model
    model = (
        st.sidebar.selectbox("Select LLM", options=["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"])
        or "llama3-70b-8192"
    )
    # Set llm in session state
    if "model" not in st.session_state:
        st.session_state["model"] = model
    # Restart the assistant if model changes
    elif st.session_state["model"] != model:
        st.session_state["model"] = model
        restart_assistant()

    search_type = st.sidebar.selectbox("Select Search Type", options=["Knowledge Base", "Web Search (Tavily)"])

    # Get the number of references to add to the prompt
    max_references = 10
    default_references = 3
    num_documents = st.sidebar.number_input(
        "Number of References", value=default_references, min_value=1, max_value=max_references
    )
    if "prev_num_documents" not in st.session_state:
        st.session_state["prev_num_documents"] = num_documents
    if st.session_state["prev_num_documents"] != num_documents:
        st.session_state["prev_num_documents"] = num_documents
        restart_assistant()

    # Get the assistant
    research_assistant: Assistant
    if "research_assistant" not in st.session_state or st.session_state["research_assistant"] is None:
        research_assistant = get_rag_research_assistant(model=model, num_documents=num_documents)
        st.session_state["research_assistant"] = research_assistant
    else:
        research_assistant = st.session_state["research_assistant"]

    # Load knowledge base
    if research_assistant.knowledge_base:
        # -*- Add websites to knowledge base
        if "url_scrape_key" not in st.session_state:
            st.session_state["url_scrape_key"] = 0

        input_url = st.sidebar.text_input(
            "Add URL to Knowledge Base", type="default", key=st.session_state["url_scrape_key"]
        )
        add_url_button = st.sidebar.button("Add URL")
        if add_url_button:
            if input_url is not None:
                alert = st.sidebar.info("Processing URLs...", icon="ℹ️")
                if f"{input_url}_scraped" not in st.session_state:
                    scraper = WebsiteReader(chunk_size=3000, max_links=5, max_depth=1)
                    web_documents: List[Document] = scraper.read(input_url)
                    if web_documents:
                        research_assistant.knowledge_base.load_documents(web_documents, upsert=True)
                    else:
                        st.sidebar.error("Could not read website")
                    st.session_state[f"{input_url}_uploaded"] = True
                alert.empty()

        # Add PDFs to knowledge base
        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 100

        uploaded_file = st.sidebar.file_uploader(
            "Add a PDF :page_facing_up:", type="pdf", key=st.session_state["file_uploader_key"]
        )
        if uploaded_file is not None:
            alert = st.sidebar.info("Processing PDF...", icon="ℹ️")
            pdf_name = uploaded_file.name.split(".")[0]
            if f"{pdf_name}_uploaded" not in st.session_state:
                reader = PDFReader(chunk_size=3000)
                pdf_documents: List[Document] = reader.read(uploaded_file)
                if pdf_documents:
                    research_assistant.knowledge_base.load_documents(documents=pdf_documents, upsert=True)
                else:
                    st.sidebar.error("Could not read PDF")
                st.session_state[f"{pdf_name}_uploaded"] = True
            alert.empty()
            st.sidebar.success(":information_source: If the PDF throws an error, try uploading it again")

    if research_assistant.knowledge_base:
        if st.sidebar.button("Clear Knowledge Base"):
            research_assistant.knowledge_base.clear()

    # Get topic for report
    input_topic = st.text_input(
        ":female-scientist: Enter a topic",
        value="Llama 3",
    )

    # -*- Generate Research Report
    generate_report = st.button("Generate Report")
    if generate_report:
        topic_search_results = None

        if search_type == "Knowledge Base" and research_assistant.knowledge_base:
            with st.status("Searching Knowledge", expanded=True) as status:
                with st.container():
                    kb_container = st.empty()
                    kb_search_docs: List[Document] = research_assistant.knowledge_base.search(
                        query=input_topic,
                        num_documents=num_documents,  # type: ignore
                    )
                    if len(kb_search_docs) > 0:
                        kb_search_results = f"# {input_topic}\n\n"
                        for idx, doc in enumerate(kb_search_docs):
                            kb_search_results += f"## Document {idx + 1}:\n\n"
                            kb_search_results += "### Metadata:\n\n"
                            kb_search_results += f"{json.dumps(doc.meta_data, indent=4)}\n\n"
                            kb_search_results += "### Content:\n\n"
                            kb_search_results += f"{doc.content}\n\n\n"
                            topic_search_results = kb_search_results
                        kb_container.markdown(kb_search_results)
                status.update(label="Knowledge Search Complete", state="complete", expanded=False)
        elif search_type == "Web Search (Tavily)":
            with st.status("Searching Web", expanded=True) as status:
                with st.container():
                    tavily_container = st.empty()
                    tavily_search_results = TavilyTools().web_search_using_tavily(
                        query=input_topic,
                        max_results=num_documents,  # type: ignore
                    )
                    if tavily_search_results:
                        topic_search_results = tavily_search_results
                        tavily_container.markdown(tavily_search_results)
                status.update(label="Web Search Complete", state="complete", expanded=False)

        if not topic_search_results:
            st.write("Sorry could not generate any search results. Please try again.")
            return

        with st.spinner("Generating Report"):
            final_report = ""
            final_report_container = st.empty()
            report_message = f"Task: Please generate a report about: {input_topic}\n\n"
            report_message += f"Here is more information about: {input_topic}\n\n"
            report_message += topic_search_results
            for delta in research_assistant.run(report_message):
                final_report += delta  # type: ignore
                final_report_container.markdown(final_report)

    if st.sidebar.button("New Run"):
        restart_assistant()


main()
