import json
from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.document import Document
from phi.tools.tavily import TavilyTools
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.tools.streamlit.components import reload_button_sidebar
from phi.utils.log import logger

from assistants import get_research_assistant  # type: ignore

st.set_page_config(
    page_title="Research Assistant",
    page_icon=":orange_heart:",
)
st.title("Research Assistant")
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
    llm_model = (
        st.sidebar.selectbox(
            "Select LLM", options=["llama3-70b-8192", "llama3", "phi3", "gpt-4-turbo", "gpt-3.5-turbo"]
        )
        or "gpt-4-turbo"
    )
    # Set llm in session state
    if "llm_model" not in st.session_state:
        st.session_state["llm_model"] = llm_model
    # Restart the assistant if llm_model changes
    elif st.session_state["llm_model"] != llm_model:
        st.session_state["llm_model"] = llm_model
        restart_assistant()

    search_type = st.sidebar.selectbox("Select Search Type", options=["Knowledge Base", "Web Search (Tavily)"])

    # Set chunk size based on llm_model
    chunk_size = 3000 if llm_model.startswith("gpt") else 2000

    # Get the number of references to add to the prompt
    max_references = 10 if llm_model.startswith("gpt") else 4
    default_references = 5 if llm_model.startswith("gpt") else 3
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
        logger.info(f"---*--- Creating {llm_model} Assistant ---*---")
        research_assistant = get_research_assistant(
            llm_model=llm_model,
            num_documents=num_documents,
        )
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
                    scraper = WebsiteReader(chunk_size=chunk_size, max_links=5, max_depth=1)
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
                reader = PDFReader(chunk_size=chunk_size)
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
            research_assistant.knowledge_base.delete()

    # Show reload button
    reload_button_sidebar()
    # Get topic for report
    input_topic = st.text_input(
        ":female-scientist: Enter a topic",
        value="SingleStore Vector Search",
    )

    # -*- Generate Research Report
    generate_report = st.button("Generate Report")
    if generate_report:
        topic_search_results = None

        if search_type == "Knowledge Base" and research_assistant.knowledge_base:
            with st.status("Searching Knowledge", expanded=True) as status:
                with st.container():
                    kb_container = st.empty()
                    kb_search_docs: List[Document] = research_assistant.knowledge_base.search(input_topic)
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
                    tavily_search_results = TavilyTools().web_search_using_tavily(input_topic)
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
        #
        # message = f"Please generate a report about: {input_topic}"
        # with st.spinner("Generating Report"):
        #     final_report = ""
        #     final_report_container = st.empty()
        #     for delta in research_assistant.run(message):
        #         final_report += delta  # type: ignore
        #         final_report_container.markdown(final_report)

    st.sidebar.success(
        ":white_check_mark: When changing the LLMs, please reload your documents as the vector store table also changes.",
    )


main()
