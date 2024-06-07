from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.tools.streamlit.components import reload_button_sidebar
from phi.utils.log import logger

from assistant import get_mistral_assistant  # type: ignore

st.set_page_config(
    page_title="Mistral RAG",
    page_icon=":orange_heart:",
)
st.title("Mistral RAG with PgVector")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    st.session_state["mistral_assistant"] = None
    st.session_state["mistral_assistant_run_id"] = None
    if "url_scrape_key" in st.session_state:
        st.session_state["url_scrape_key"] += 1
    if "file_uploader_key" in st.session_state:
        st.session_state["file_uploader_key"] += 1
    st.rerun()


def main() -> None:
    # Get model
    mistral_model = st.sidebar.selectbox(
        "Select Model",
        options=["open-mixtral-8x22b", "mistral-large-latest", "open-mixtral-8x7b", "mistral-medium-latest"],
    )
    # Set assistant_type in session state
    if "mistral_model" not in st.session_state:
        st.session_state["mistral_model"] = mistral_model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["mistral_model"] != mistral_model:
        st.session_state["mistral_model"] = mistral_model
        restart_assistant()

    # Get the assistant
    mistral_assistant: Assistant
    if "mistral_assistant" not in st.session_state or st.session_state["mistral_assistant"] is None:
        logger.info(f"---*--- Creating {mistral_model} Assistant ---*---")
        mistral_assistant = get_mistral_assistant(
            model=mistral_model,
        )
        st.session_state["mistral_assistant"] = mistral_assistant
    else:
        mistral_assistant = st.session_state["mistral_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    try:
        st.session_state["mistral_assistant_run_id"] = mistral_assistant.create_run()
    except Exception:
        st.warning("Could not create assistant, is the database running?")
        return

    # Load existing messages
    assistant_chat_history = mistral_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
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
            for delta in mistral_assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    # Load knowledge base
    if mistral_assistant.knowledge_base:
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
                    scraper = WebsiteReader(max_links=10, max_depth=2)
                    web_documents: List[Document] = scraper.read(input_url)
                    if web_documents:
                        mistral_assistant.knowledge_base.load_documents(web_documents, upsert=True)
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
            alert = st.sidebar.info("Processing PDF...", icon="🧠")
            mistral_rag_name = uploaded_file.name.split(".")[0]
            if f"{mistral_rag_name}_uploaded" not in st.session_state:
                reader = PDFReader()
                mistral_rag_documents: List[Document] = reader.read(uploaded_file)
                if mistral_rag_documents:
                    mistral_assistant.knowledge_base.load_documents(mistral_rag_documents, upsert=True)
                else:
                    st.sidebar.error("Could not read PDF")
                st.session_state[f"{mistral_rag_name}_uploaded"] = True
            alert.empty()

    if mistral_assistant.knowledge_base and mistral_assistant.knowledge_base.vector_db:
        if st.sidebar.button("Clear Knowledge Base"):
            mistral_assistant.knowledge_base.vector_db.clear()
            st.session_state["mistral_rag_knowledge_base_loaded"] = False
            st.sidebar.success("Knowledge base cleared")

    if mistral_assistant.storage:
        mistral_assistant_run_ids: List[str] = mistral_assistant.storage.get_all_run_ids()
        new_mistral_assistant_run_id = st.sidebar.selectbox("Run ID", options=mistral_assistant_run_ids)
        if st.session_state["mistral_assistant_run_id"] != new_mistral_assistant_run_id:
            logger.info(f"---*--- Loading {mistral_model} run: {new_mistral_assistant_run_id} ---*---")
            st.session_state["mistral_assistant"] = get_mistral_assistant(
                model=mistral_model, run_id=new_mistral_assistant_run_id
            )
            st.rerun()

    if st.sidebar.button("New Run"):
        restart_assistant()

    # Show reload button
    reload_button_sidebar()


main()
