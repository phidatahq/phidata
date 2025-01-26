from typing import Iterator

import streamlit as st
from agents import get_sql_agent
from agno.agent import Agent, RunResponse
from agno.utils.log import logger

# Page configuration
st.set_page_config(
    page_title="F1 SQL Agent",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS with dark mode support
st.markdown(
    """
    <style>
    /* Main Styles */
    .main-title {
        text-align: center;
        background: linear-gradient(45deg, #FF4B2B, #FF416C);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em;
        font-weight: bold;
        padding: 1em 0;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2em;
    }
    .stButton button {
        width: 100%;
        border-radius: 20px;
        margin: 0.2em 0;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .chat-container {
        border-radius: 15px;
        padding: 1em;
        margin: 1em 0;
        background-color: #f5f5f5;
    }
    .sql-result {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1em;
        margin: 1em 0;
        border-left: 4px solid #FF4B2B;
    }
    .status-message {
        padding: 1em;
        border-radius: 10px;
        margin: 1em 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
    }
    /* Dark mode adjustments */
    @media (prefers-color-scheme: dark) {
        .chat-container {
            background-color: #2b2b2b;
        }
        .sql-result {
            background-color: #1e1e1e;
        }
    }
    </style>
""",
    unsafe_allow_html=True,
)


def load_data_and_knowledge():
    """Load F1 data and knowledge base if not already done"""
    from load_f1_data import load_f1_data
    from load_knowledge import load_knowledge

    if "data_loaded" not in st.session_state:
        with st.spinner("🔄 Loading F1 data into database..."):
            load_f1_data()
        with st.spinner("📚 Loading knowledge base..."):
            load_knowledge()
        st.session_state["data_loaded"] = True
        st.success("✅ F1 data and knowledge loaded successfully!")


def add_message(role: str, content: str) -> None:
    """Safely add a message to the session state"""
    if "messages" not in st.session_state or not isinstance(
        st.session_state["messages"], list
    ):
        st.session_state["messages"] = []
    st.session_state["messages"].append({"role": role, "content": content})


def restart_agent():
    """Reset the agent and clear chat history"""
    logger.debug("---*--- Restarting agent ---*---")
    st.session_state["sql_agent"] = None
    st.session_state["messages"] = []
    st.rerun()


def export_chat_history():
    """Export chat history as markdown"""
    if "messages" in st.session_state:
        chat_text = "# F1 SQL Agent - Chat History\n\n"
        for msg in st.session_state["messages"]:
            role = "🤖 Assistant" if msg["role"] == "agent" else "👤 User"
            chat_text += f"### {role}\n{msg['content']}\n\n"
        return chat_text
    return ""


def main() -> None:
    # Header
    st.markdown("<h1 class='main-title'>F1 SQL Agent</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Your intelligent F1 data companion powered by Agno</p>",
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
        - 📊 SQL
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
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": "👋 Ask me anything about F1 data from 1950 to 2020!",
            }
        ]

    # Main chat interface
    chat_container = st.container()
    with chat_container:
        # Clear the container before displaying messages
        st.empty()

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
                        run_response: Iterator[RunResponse] = sql_agent.run(
                            question, stream=True
                        )
                        for _resp_chunk in run_response:
                            if _resp_chunk.content is not None:
                                response += _resp_chunk.content
                                try:
                                    resp_container.markdown(response)
                                except Exception as e:
                                    st.error(f"Error updating response: {str(e)}")
                                    break
                        st.session_state["messages"].append(
                            {"role": "assistant", "content": response}
                        )
                    except Exception as e:
                        error_message = f"Sorry, I encountered an error: {str(e)}"
                        st.error(error_message)
                        st.session_state["messages"].append(
                            {"role": "assistant", "content": error_message}
                        )

        # Get user input
        if prompt := st.chat_input("Ask about F1 data..."):
            add_message("user", prompt)


if __name__ == "__main__":
    main()
