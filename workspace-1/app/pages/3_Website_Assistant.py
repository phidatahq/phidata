from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.tools.streamlit.components import (
    get_openai_key_sidebar,
    check_password,
    reload_button_sidebar,
    get_username_sidebar,
)

from ai.assistants.website_auto import get_autonomous_website_assistant
from ai.assistants.website_rag import get_rag_website_assistant
from utils.log import logger

st.set_page_config(
    page_title="Website AI",
    page_icon=":orange_heart:",
)
st.title("Website Assistant")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    st.session_state["website_assistant"] = None
    st.session_state["website_assistant_run_id"] = None
    st.rerun()


def main() -> None:
    # Get OpenAI key from environment variable or user input
    get_openai_key_sidebar()

    # Get username
    username = get_username_sidebar()
    if username:
        st.sidebar.info(f":technologist: User: {username}")
    else:
        st.markdown("---")
        st.markdown("#### :technologist: Enter a username, load a website and start chatting")
        return

    # Get assistant type
    website_assistant_type = st.sidebar.selectbox("Assistant Type", options=["Autonomous", "RAG"])
    # Set assistant_type in session state
    if "website_assistant_type" not in st.session_state:
        st.session_state["website_assistant_type"] = website_assistant_type
    # Restart the assistant if assistant_type has changed
    elif st.session_state["website_assistant_type"] != website_assistant_type:
        st.session_state["website_assistant_type"] = website_assistant_type
        restart_assistant()

    # Get the assistant
    website_assistant: Assistant
    if "website_assistant" not in st.session_state or st.session_state["website_assistant"] is None:
        if st.session_state["website_assistant_type"] == "Autonomous":
            logger.info("---*--- Creating Autonomous Assistant ---*---")
            website_assistant = get_autonomous_website_assistant(
                user_id=username,
                debug_mode=True,
            )
        else:
            logger.info("---*--- Creating RAG Assistant ---*---")
            website_assistant = get_rag_website_assistant(
                user_id=username,
                debug_mode=True,
            )
        st.session_state["website_assistant"] = website_assistant
    else:
        website_assistant = st.session_state["website_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    st.session_state["website_assistant_run_id"] = website_assistant.create_run()

    # Check if knowlege base exists
    if website_assistant.knowledge_base and (
        "website_knowledge_base_loaded" not in st.session_state
        or not st.session_state["website_knowledge_base_loaded"]
    ):
        if not website_assistant.knowledge_base.exists():
            loading_container = st.sidebar.info("🧠 Loading knowledge base")
            website_assistant.knowledge_base.load()
            st.session_state["website_knowledge_base_loaded"] = True
            st.sidebar.success("Knowledge Base loaded")
            loading_container.empty()

    # Load messages for existing assistant
    assistant_chat_history = website_assistant.memory.get_chat_history()
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
    if last_message.get("role", "") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            with st.spinner("Working..."):
                response = ""
                resp_container = st.empty()
                for delta in website_assistant.run(question):
                    response += delta  # type: ignore
                    resp_container.markdown(response)

            st.session_state["messages"].append({"role": "assistant", "content": response})

    if st.sidebar.button("New Run"):
        restart_assistant()

    if website_assistant.knowledge_base:
        if st.sidebar.button("Update Knowledge Base"):
            website_assistant.knowledge_base.load(recreate=False, upsert=True)
            st.session_state["knowledge_base_exists"] = True
            st.sidebar.success("Knowledge base updated")

        if st.sidebar.button("Recreate Knowledge Base"):
            website_assistant.knowledge_base.load(recreate=True)
            st.session_state["knowledge_base_exists"] = True
            st.sidebar.success("Knowledge base recreated")

        if st.sidebar.button("Clear Knowledge Base"):
            if website_assistant.knowledge_base.vector_db:
                website_assistant.knowledge_base.vector_db.clear()
                st.session_state["pdf_knowledge_base_loaded"] = False
                st.sidebar.success("Knowledge base cleared")

    if st.sidebar.button("Auto Rename"):
        website_assistant.auto_rename_run()

    # Add websites to knowledge base
    website_knowledge_base: WebsiteKnowledgeBase = website_assistant.knowledge_base  # type: ignore
    if website_knowledge_base:
        website_url = st.sidebar.text_input("Add Website to Knowledge Base")
        if website_url != "" and website_url not in website_knowledge_base.urls:
            website_knowledge_base.urls.append(website_url)
            loading_container = st.sidebar.info(f"🧠 Loading {website_url}")
            website_knowledge_base.load()
            st.session_state["website_knowledge_base_loaded"] = True
            loading_container.empty()

    if website_assistant.storage:
        website_assistant_run_ids: List[str] = website_assistant.storage.get_all_run_ids(user_id=username)
        new_website_assistant_run_id = st.sidebar.selectbox("Run ID", options=website_assistant_run_ids)
        if st.session_state["website_assistant_run_id"] != new_website_assistant_run_id:
            logger.debug(f"Loading run {new_website_assistant_run_id}")
            if st.session_state["website_assistant_type"] == "Autonomous":
                logger.info("---*--- Loading as Autonomous Assistant ---*---")
                st.session_state["website_assistant"] = get_autonomous_website_assistant(
                    user_id=username,
                    run_id=new_website_assistant_run_id,
                    debug_mode=True,
                )
            else:
                logger.info("---*--- Loading as RAG Assistant ---*---")
                st.session_state["website_assistant"] = get_rag_website_assistant(
                    user_id=username,
                    run_id=new_website_assistant_run_id,
                    debug_mode=True,
                )
            st.rerun()

    website_assistant_run_name = website_assistant.run_name
    if website_assistant_run_name:
        st.sidebar.write(f":thread: {website_assistant_run_name}")

    # Show reload button
    reload_button_sidebar()


if check_password():
    main()
