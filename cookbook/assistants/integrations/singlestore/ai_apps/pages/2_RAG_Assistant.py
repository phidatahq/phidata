from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.tools.streamlit.components import reload_button_sidebar
from phi.utils.log import logger

from assistants import get_rag_assistant  # type: ignore

st.set_page_config(
    page_title="RAG Assistant",
    page_icon=":orange_heart:",
)
st.title("RAG Assistant")
st.markdown("##### :orange_heart: Built with [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["rag_assistant"] = None
    st.session_state["rag_assistant_run_id"] = None
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
    rag_assistant: Assistant
    if "rag_assistant" not in st.session_state or st.session_state["rag_assistant"] is None:
        logger.info(f"---*--- Creating {llm_model} Assistant ---*---")
        rag_assistant = get_rag_assistant(
            llm_model=llm_model,
            num_documents=num_documents,
        )
        st.session_state["rag_assistant"] = rag_assistant
    else:
        rag_assistant = st.session_state["rag_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    try:
        st.session_state["rag_assistant_run_id"] = rag_assistant.create_run()
    except Exception:
        st.warning("Could not create assistant, is the database running?")
        return

    # Load existing messages
    rag_assistant_chat_history = rag_assistant.memory.get_chat_history()
    if len(rag_assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = rag_assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Upload a doc and ask me questions..."}]

    # Prompt for user input
    if prompt := st.chat_input():
        st.session_state["messages"].append({"role": "user", "content": prompt})

    # Display existing chat messages
    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # If last message is from a user, generate a new response
    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            response = ""
            resp_container = st.empty()
            for delta in rag_assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    # Load knowledge base
    if rag_assistant.knowledge_base:
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
                        rag_assistant.knowledge_base.load_documents(web_documents, upsert=True)
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
                    rag_assistant.knowledge_base.load_documents(documents=pdf_documents, upsert=True)
                else:
                    st.sidebar.error("Could not read PDF")
                st.session_state[f"{pdf_name}_uploaded"] = True
            alert.empty()
            st.sidebar.success(":information_source: If the PDF throws an error, try uploading it again")

    if rag_assistant.storage:
        assistant_run_ids: List[str] = rag_assistant.storage.get_all_run_ids()
        new_assistant_run_id = st.sidebar.selectbox("Run ID", options=assistant_run_ids)
        if new_assistant_run_id is not None and st.session_state["rag_assistant_run_id"] != new_assistant_run_id:
            logger.info(f"---*--- Loading run: {new_assistant_run_id} ---*---")
            st.session_state["rag_assistant"] = get_rag_assistant(
                llm_model=llm_model,
                run_id=new_assistant_run_id,
                num_documents=num_documents,
            )
            st.rerun()

    assistant_run_name = rag_assistant.run_name
    if assistant_run_name:
        st.sidebar.write(f":thread: {assistant_run_name}")

    if st.sidebar.button("New Run"):
        restart_assistant()

    if st.sidebar.button("Auto Rename"):
        rag_assistant.auto_rename_run()

    if rag_assistant.knowledge_base:
        if st.sidebar.button("Clear Knowledge Base"):
            rag_assistant.knowledge_base.delete()

    # Show reload button
    reload_button_sidebar()

    st.sidebar.success(
        ":white_check_mark: When changing the LLM between OpenAI and OSS, please reload your documents as the vector store table will also change.",
    )


main()
