from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.website import WebsiteReader
from phi.tools.streamlit.components import (
    check_password,
    reload_button_sidebar,
    get_username_sidebar,
)

from assistant import get_local_rag_assistant  # Adjust the import statement as needed
from logging import getLogger

logger = getLogger(__name__)

st.set_page_config(
    page_title="Local RAG with Web Scraping \n Using SingleStore as a backend databse",
    page_icon=":orange_heart:",
)
st.title("Local RAG with Web Scraping")
st.markdown("##### :orange_heart: Built using [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    st.session_state["web_assistant"] = None
    st.session_state["web_assistant_run_id"] = None
    st.session_state["url_scrape_key"] += 1
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
    local_rag_model = st.sidebar.selectbox("Select Model", options=["GPT-4", "Hermes2", "Claude"])
    # Set assistant_type in session state
    if "local_rag_model" not in st.session_state:
        st.session_state["local_rag_model"] = local_rag_model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["local_rag_model"] != local_rag_model:
        st.session_state["local_rag_model"] = local_rag_model
        restart_assistant()

    # Get the assistant
    web_assistant: Assistant
    if "web_assistant" not in st.session_state or st.session_state["web_assistant"] is None:
        logger.info("---*--- Creating Web Assistant ---*---")
        web_assistant = get_local_rag_assistant(
            model=local_rag_model,
            user_id=username,
            debug_mode=True,
        )
        st.session_state["web_assistant"] = web_assistant
    else:
        web_assistant = st.session_state["web_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    try:
        st.session_state["web_assistant_run_id"] = web_assistant.create_run()
    except Exception:
        st.warning("Could not create assistant, is the database running?")
        return

    # Load existing messages
    assistant_chat_history = web_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "web_assistant", "content": "Ask me anything..."}]

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
        with st.chat_message("web_assistant"):
            response = ""
            resp_container = st.empty()
            for delta in web_assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)

            st.session_state["messages"].append({"role": "web_assistant", "content": response})

    if st.sidebar.button("New Run"):
        restart_assistant()

    if st.sidebar.button("Auto Rename"):
        web_assistant.auto_rename_run()

    # Upload Web Content
    if web_assistant.knowledge_base:
        if "url_scrape_key" not in st.session_state:
            st.session_state["url_scrape_key"] = 0

        scraped_url = st.sidebar.text_input("Input URL", type="default", key=st.session_state["url_scrape_key"])
        append_button = st.sidebar.button("Search URL")
        if append_button:
            if scraped_url is not None:
                alert = st.sidebar.info("Processing URLs...", icon="🧠")
                if f"{scraped_url}_scraped" not in st.session_state:
                    scraper = WebsiteReader()
                    web_documents: List[Document] = scraper.read(scraped_url)
                    if web_documents:
                        web_assistant.knowledge_base.load_documents(web_documents, upsert=True, skip_existing=True)
                    else:
                        st.sidebar.error("Could not read Website")
                    st.session_state[f"{scraped_url}_uploaded"] = True
                alert.empty()

    if web_assistant.storage:
        web_assistant_run_ids: List[str] = web_assistant.storage.get_all_run_ids(user_id=username)
        new_web_assistant_run_id = st.sidebar.selectbox("Run ID", options=web_assistant_run_ids)
        if st.session_state["web_assistant_run_id"] != new_web_assistant_run_id:
            logger.info(f"---*--- Loading run: {new_web_assistant_run_id} ---*---")
            st.session_state["web_assistant"] = get_local_rag_assistant(
                model=local_rag_model,
                user_id=username,
                run_id=new_web_assistant_run_id,
                debug_mode=True,
            )
            st.rerun()

    web_assistant_run_name = web_assistant.run_name
    if web_assistant_run_name:
        st.sidebar.write(f":thread: {web_assistant_run_name}")

    # Show reload button
    reload_button_sidebar()


if check_password():
    main()
