from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.tools.streamlit.components import (
    check_password,
    reload_button_sidebar,
    get_username_sidebar,
)

from groq_assistant import get_groq_assistant  # type: ignore
from logging import getLogger

logger = getLogger(__name__)

st.set_page_config(
    page_title="Groq RAG",
    page_icon=":orange_heart:",
)
st.title("RAG using Groq and PgVector")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    st.session_state["groq_assistant"] = None
    st.session_state["groq_assistant_run_id"] = None
    st.session_state["file_uploader_key"] += 1
    st.rerun()


def main() -> None:
    # Get username
    username = get_username_sidebar()
    if username:
        st.sidebar.info(f":technologist: User: {username}")
    else:
        st.write(":technologist: Please enter a username")
        return

    # Get model
    groq_model = st.sidebar.selectbox("Select Model", options=["mixtral-8x7b-32768", "llama2-70b-4096"])
    # Set assistant_type in session state
    if "groq_model" not in st.session_state:
        st.session_state["groq_model"] = groq_model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["groq_model"] != groq_model:
        st.session_state["groq_model"] = groq_model
        restart_assistant()

    # Get the assistant
    groq_assistant: Assistant
    if "groq_assistant" not in st.session_state or st.session_state["groq_assistant"] is None:
        logger.info(f"---*--- Creating {groq_model} Assistant ---*---")
        groq_assistant = get_groq_assistant(
            model=groq_model,
            user_id=username,
            debug_mode=True,
        )
        st.session_state["groq_assistant"] = groq_assistant
    else:
        groq_assistant = st.session_state["groq_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    try:
        st.session_state["groq_assistant_run_id"] = groq_assistant.create_run()
    except Exception:
        st.warning("Could not create assistant, is the database running?")
        return

    # Load existing messages
    assistant_chat_history = groq_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me anything..."}]

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
            for delta in groq_assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)

            st.session_state["messages"].append({"role": "assistant", "content": response})

    if st.sidebar.button("New Run"):
        restart_assistant()

    if groq_assistant.knowledge_base and groq_assistant.knowledge_base.vector_db:
        if st.sidebar.button("Clear Knowledge Base"):
            groq_assistant.knowledge_base.vector_db.clear()
            st.session_state["groq_rag_knowledge_base_loaded"] = False
            st.sidebar.success("Knowledge base cleared")

    if st.sidebar.button("Auto Rename"):
        groq_assistant.auto_rename_run()

    # Upload PDF
    if groq_assistant.knowledge_base:
        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 0

        uploaded_file = st.sidebar.file_uploader(
            "Upload PDF",
            type="pdf",
            key=st.session_state["file_uploader_key"],
        )
        if uploaded_file is not None:
            alert = st.sidebar.info("Processing PDF...", icon="🧠")
            groq_rag_name = uploaded_file.name.split(".")[0]
            if f"{groq_rag_name}_uploaded" not in st.session_state:
                reader = PDFReader()
                groq_rag_documents: List[Document] = reader.read(uploaded_file)
                if groq_rag_documents:
                    groq_assistant.knowledge_base.load_documents(groq_rag_documents, upsert=True)
                else:
                    st.sidebar.error("Could not read PDF")
                st.session_state[f"{groq_rag_name}_uploaded"] = True
            alert.empty()

    if groq_assistant.storage:
        groq_assistant_run_ids: List[str] = groq_assistant.storage.get_all_run_ids(user_id=username)
        new_groq_assistant_run_id = st.sidebar.selectbox("Run ID", options=groq_assistant_run_ids)
        if st.session_state["groq_assistant_run_id"] != new_groq_assistant_run_id:
            logger.info(f"---*--- Loading {groq_model} run: {new_groq_assistant_run_id} ---*---")
            st.session_state["groq_assistant"] = get_groq_assistant(
                model=groq_model,
                user_id=username,
                run_id=new_groq_assistant_run_id,
                debug_mode=True,
            )
            st.rerun()

    groq_assistant_run_name = groq_assistant.run_name
    if groq_assistant_run_name:
        st.sidebar.write(f":thread: {groq_assistant_run_name}")

    # Show reload button
    reload_button_sidebar()


if check_password():
    main()
