from typing import List

import streamlit as st
from phi.assistant import Assistant
from phi.utils.log import logger

from assistant import get_sql_assistant


st.set_page_config(
    page_title="SQL Assistant",
    page_icon=":orange_heart:",
)
st.title("SQL Assistant")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")
with st.expander(":rainbow[:point_down: Example Questions]"):
    st.markdown("- Which driver has the most race wins?")
    st.markdown("- Which team won the most Constructors Championships?")


def main() -> None:
    # Get the assistant
    sql_assistant: Assistant
    if "sql_assistant" not in st.session_state or st.session_state["sql_assistant"] is None:
        if "sql_assistant_run_id" in st.session_state and st.session_state["sql_assistant_run_id"] is not None:
            logger.info("---*--- Reading SQL Assistant ---*---")
            sql_assistant = get_sql_assistant(run_id=st.session_state["sql_assistant_run_id"])
        else:
            logger.info("---*--- Creating new SQL Assistant ---*---")
            sql_assistant = get_sql_assistant()
        st.session_state["sql_assistant"] = sql_assistant
    else:
        sql_assistant = st.session_state["sql_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    st.session_state["sql_assistant_run_id"] = sql_assistant.create_run()

    # Load existing messages
    assistant_chat_history = sql_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me about F1 data from 1950 to 2020."}]

    # Prompt for user input
    if prompt := st.chat_input():
        st.session_state["messages"].append({"role": "user", "content": prompt})

    # Sample buttons
    if st.sidebar.button("Show tables"):
        _message = "Which tables do you have access to?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Describe tables"):
        _message = "Tell me more about these tables."
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Most Race Wins"):
        _message = "Which driver has the most race wins?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Most Constructors Championships"):
        _message = "Which team won the most Constructors Championships?"
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Longest Racing Career"):
        _message = "Tell me the name of the driver with the longest racing career? Also tell me when they started and when they retired."
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Races per year"):
        _message = "Show me the number of races per year."
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button("Team position for driver with most wins"):
        _message = "Write a query to identify the drivers that won the most races per year from 2010 onwards and the position of their team that year."
        st.session_state["messages"].append({"role": "user", "content": _message})

    if st.sidebar.button(":orange_heart: This is awesome!"):
        _message = "You're awesome!"
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
                for delta in sql_assistant.run(question):
                    response += delta  # type: ignore
                    resp_container.markdown(response)
                st.session_state["messages"].append({"role": "assistant", "content": response})

    st.sidebar.markdown("---")

    if st.sidebar.button("New Run"):
        restart_assistant()

    if st.sidebar.button("Auto Rename Thread"):
        sql_assistant.auto_rename_run()

    if sql_assistant.storage:
        sql_assistant_run_ids: List[str] = sql_assistant.storage.get_all_run_ids()
        new_sql_assistant_run_id = st.sidebar.selectbox("Run ID", options=sql_assistant_run_ids)
        if st.session_state["sql_assistant_run_id"] != new_sql_assistant_run_id:
            logger.info(f"Loading run {new_sql_assistant_run_id}")
            st.session_state["sql_assistant"] = get_sql_assistant(
                run_id=new_sql_assistant_run_id,
                debug_mode=True,
            )
            st.rerun()

    sql_assistant_run_name = sql_assistant.run_name
    if sql_assistant_run_name:
        st.sidebar.write(f":thread: {sql_assistant_run_name}")


def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["sql_assistant"] = None
    st.session_state["sql_assistant_run_id"] = None
    st.rerun()


main()
