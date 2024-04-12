from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.tools.streamlit.components import (
    get_openai_key_sidebar,
    get_username_sidebar,
    check_password,
)

from nyc.assistant import get_nyc_assistant
from utils.log import logger


st.set_page_config(
    page_title="NYC Data AI",
    page_icon=":orange_heart:",
)
st.title("NYC Data AI")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")
with st.expander(":rainbow[:point_down: Example Questions]"):
    st.markdown("- Which tables do you have access to?")
    st.markdown("- Whats the total 2023 pay for `DEPARTMENT OF PROBATION`?")
    st.markdown("- Who is the highest paid employee in 2023?")
    st.markdown("- Who earned the highest overtime wages in 2023?")
    st.markdown("- Which agency had the highest overtime pay?")
    st.markdown("- How many agencies are there in nyc?")


def restart_assistant():
    st.session_state["nyc_assistant"] = None
    st.session_state["nyc_assistant_run_id"] = None
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
        st.markdown("#### :technologist: Enter a username and start chatting with the NYC Data AI")
        return

    # Get the assistant
    nyc_assistant: Assistant
    if "nyc_assistant" not in st.session_state or st.session_state["nyc_assistant"] is None:
        logger.info("---*--- Creating NYC Assistant ---*---")
        nyc_assistant = get_nyc_assistant(
            user_id=username,
            debug_mode=True,
        )
        st.session_state["nyc_assistant"] = nyc_assistant
    else:
        nyc_assistant = st.session_state["nyc_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    st.session_state["nyc_assistant_run_id"] = nyc_assistant.create_run()

    # Check if knowlege base exists
    if nyc_assistant.knowledge_base and (
        "oceangpt_kb_loaded" not in st.session_state or not st.session_state["oceangpt_kb_loaded"]
    ):
        if not nyc_assistant.knowledge_base.exists():
            logger.info("Knowledge base does not exist")
            loading_container = st.sidebar.info("🧠 Loading knowledge base")
            nyc_assistant.knowledge_base.load()
            st.session_state["oceangpt_kb_loaded"] = True
            st.sidebar.success("Knowledge base loaded")
            loading_container.empty()

    # Load messages for existing assistant
    assistant_chat_history = nyc_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me about what's on NYC"}]

    # Prompt for user input
    if prompt := st.chat_input():
        st.session_state["messages"].append({"role": "user", "content": prompt})

    if st.sidebar.button(":orange_heart: This is awesome!"):
        _message = "You're awesome!"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Show tables"):
        _message = "Which tables do you have access to?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("2023 Overtime analysis"):
        _message = "Conduct an analysis on overtime pay in 2023, show results as a table?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Total pay for all NYC Agencies in 2023"):
        _message = "Whats the total 2023 pay for all NYC agencies?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Top 5 agencies by total pay"):
        _message = "Show me the top 5 agencies by total pay in a table?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Total pay for DEPARTMENT OF PROBATION in 2023"):
        _message = "Whats the total 2023 pay for `DEPARTMENT OF PROBATION`?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Highest paid employee in 2023"):
        _message = "Who is the highest paid employee in 2023?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Highest overtime wages in 2023"):
        _message = "Who earned the highest overtime wages in 2023?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Agency with the highest overtime pay"):
        _message = "Which agency had the highest overtime pay?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("How many agencies are there"):
        _message = "How many agencies are there in nyc?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Employees per agency in 2023"):
        _message = "Show me the employees per agency in 2023?"
        st.session_state["messages"].append({"role": "user", "content": _message})

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
            with st.spinner("Working..."):
                response = ""
                resp_container = st.empty()
                for delta in nyc_assistant.run(question):
                    response += delta  # type: ignore
                    resp_container.markdown(response)

                st.session_state["messages"].append({"role": "assistant", "content": response})

    st.sidebar.markdown("---")

    if st.sidebar.button("New Run"):
        restart_assistant()

    if st.sidebar.button("Auto Rename"):
        nyc_assistant.auto_rename_run()

    if nyc_assistant.storage:
        hn_assistant_run_ids: List[str] = nyc_assistant.storage.get_all_run_ids(user_id=username)
        new_nyc_assistant_run_id = st.sidebar.selectbox("Run ID", options=hn_assistant_run_ids)
        if st.session_state["nyc_assistant_run_id"] != new_nyc_assistant_run_id:
            logger.debug(f"Loading run {new_nyc_assistant_run_id}")
            logger.info("---*--- Loading NYC Assistant ---*---")
            st.session_state["nyc_assistant"] = get_nyc_assistant(
                user_id=username,
                run_id=new_nyc_assistant_run_id,
                debug_mode=True,
            )
            st.rerun()

    nyc_assistant_run_name = nyc_assistant.run_name
    if nyc_assistant_run_name:
        st.sidebar.write(f":thread: {nyc_assistant_run_name}")


if check_password():
    main()
