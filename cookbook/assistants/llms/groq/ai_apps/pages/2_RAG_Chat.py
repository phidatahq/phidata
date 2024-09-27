from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.utils.log import logger

from assistants import get_rag_chat_assistant  # type: ignore

st.set_page_config(
    page_title="RAG Chat Assistant",
    page_icon=":orange_heart:",
)
st.title("RAG Chat Assistant")
st.markdown("##### :orange_heart: Built with [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["chat_assistant"] = None
    st.session_state["chat_assistant_run_id"] = None
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
    chat_assistant: Assistant
    if "chat_assistant" not in st.session_state or st.session_state["chat_assistant"] is None:
        chat_assistant = get_rag_chat_assistant(
            model=model,
            num_documents=num_documents,
        )
        st.session_state["chat_assistant"] = chat_assistant
    else:
        chat_assistant = st.session_state["chat_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    try:
        st.session_state["chat_assistant_run_id"] = chat_assistant.create_run()
    except Exception:
        st.warning("Could not create assistant, is the database running?")
        return

    # Load existing messages
    chat_assistant_chat_history = chat_assistant.memory.get_chat_history()
    if len(chat_assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = chat_assistant_chat_history
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
            for delta in chat_assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    # Load knowledge base
    if chat_assistant.knowledge_base:
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
                        chat_assistant.knowledge_base.load_documents(web_documents, upsert=True)
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
                    chat_assistant.knowledge_base.load_documents(documents=pdf_documents, upsert=True)
                else:
                    st.sidebar.error("Could not read PDF")
                st.session_state[f"{pdf_name}_uploaded"] = True
            alert.empty()
            st.sidebar.success(":information_source: If the PDF throws an error, try uploading it again")

    if chat_assistant.storage:
        assistant_run_ids: List[str] = chat_assistant.storage.get_all_run_ids()
        new_assistant_run_id = st.sidebar.selectbox("Run ID", options=assistant_run_ids)
        if new_assistant_run_id is not None and st.session_state["chat_assistant_run_id"] != new_assistant_run_id:
            logger.info(f"---*--- Loading run: {new_assistant_run_id} ---*---")
            st.session_state["chat_assistant"] = get_rag_chat_assistant(
                model=model,
                run_id=new_assistant_run_id,
                num_documents=num_documents,
            )
            st.rerun()

    if chat_assistant.knowledge_base:
        if st.sidebar.button("Clear Knowledge Base"):
            chat_assistant.knowledge_base.clear()

    if st.sidebar.button("New Run"):
        restart_assistant()


main()
