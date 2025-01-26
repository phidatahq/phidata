from typing import Iterator

import streamlit as st
from agents import get_sql_agent
from agno.agent import Agent, RunResponse
from agno.utils.log import logger
from utils import (
    CUSTOM_CSS,
    add_message,
    display_tool_calls,
    export_chat_history,
    load_data_and_knowledge,
    restart_agent,
)

# Page configuration
st.set_page_config(
    page_title="F1 SQL Agent",
    page_icon=":checkered_flag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS with dark mode support
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main() -> None:
    # Header
    st.markdown("<h1 class='main-title'>F1 SQL Agent</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Your intelligent F1 data analyst powered by Agno</p>",
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        # Basic Information
        st.markdown("#### 🏎️ Basic Information")
        if st.button("📋 Show Tables"):
            add_message("user", "Which tables do you have access to?")
        if st.button("ℹ️ Describe Tables"):
            add_message("user", "Tell me more about these tables.")

        # Statistics
        st.markdown("#### 🏆 Statistics")
        if st.button("🥇 Most Race Wins"):
            add_message("user", "Which driver has the most race wins?")

        if st.button("🏆 Constructor Champs"):
            add_message("user", "Which team won the most Constructors Championships?")

        if st.button("⏳ Longest Career"):
            add_message(
                "user",
                "Tell me the name of the driver with the longest racing career? Also tell me when they started and when they retired.",
            )

        # Analysis
        st.markdown("#### 📊 Analysis")
        if st.button("📈 Races per Year"):
            add_message("user", "Show me the number of races per year.")

        if st.button("🔍 Team Performance"):
            add_message(
                "user",
                "Write a query to identify the drivers that won the most races per year from 2010 onwards and the position of their team that year.",
            )

        # Utility buttons
        st.markdown("#### 🛠️ Utilities")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Chat"):
                restart_agent()
        with col2:
            if st.download_button(
                "💾 Export Chat",
                export_chat_history(),
                file_name="f1_chat_history.md",
                mime="text/markdown",
            ):
                st.success("Chat history exported!")

        if st.sidebar.button("🚀 Load F1 Data"):
            load_data_and_knowledge()

        # About section
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        This F1 SQL Assistant helps you analyze Formula 1 data from 1950 to 2020 using natural language queries.

        Built with:
        - 🚀 Agno
        - 💫 Streamlit
        """)

    # Initialize SQL agent
    sql_agent: Agent
    if "sql_agent" not in st.session_state or st.session_state["sql_agent"] is None:
        logger.info("---*--- Creating new SQL agent ---*---")
        sql_agent = get_sql_agent()
        st.session_state["sql_agent"] = sql_agent
    else:
        sql_agent = st.session_state["sql_agent"]

    # Initialize messages
    if "messages" not in st.session_state or not isinstance(
        st.session_state["messages"], list
    ):
        st.session_state["messages"] = []

    # Get user input
    if prompt := st.chat_input("👋 Ask me about F1 data from 1950 to 2020!"):
        add_message("user", prompt)

    # Display chat history
    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Generate response for last user message
    last_message = (
        st.session_state["messages"][-1] if st.session_state["messages"] else None
    )
    if last_message and last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            resp_container = st.empty()
            with st.spinner("🤔 Thinking..."):
                response = ""
                try:
                    # Create container for tool calls
                    tool_calls_container = st.empty()

                    # Run the agent and stream the response
                    run_stream: Iterator[RunResponse] = sql_agent.run(
                        question, stream=True
                    )
                    for _resp_chunk in run_stream:
                        # Display tool calls if available
                        if _resp_chunk.tools and len(_resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, _resp_chunk.tools)

                        # Display response
                        if _resp_chunk.content is not None:
                            response += _resp_chunk.content
                            resp_container.markdown(response)

                    st.session_state["messages"].append(
                        {"role": "assistant", "content": response}
                    )
                except Exception as e:
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_message)
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": error_message}
                    )


if __name__ == "__main__":
    main()
