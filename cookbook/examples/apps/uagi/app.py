import nest_asyncio
import streamlit as st
from agents import get_uagi
from agno.agent import Agent
from agno.utils.log import logger
from utils import (
    CUSTOM_CSS,
    about_widget,
    add_message,
    display_team_memory,
    display_tool_calls,
    knowledge_manager,
    session_manager,
    sidebar_widget,
)

nest_asyncio.apply()

# Page configuration
st.set_page_config(
    page_title="UAgI",
    page_icon=":checkered_flag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS with dark mode support
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main() -> None:
    ####################################################################
    # App header
    ####################################################################
    st.markdown(
        "<h1 class='main-title'>Universal Agent Interface</h1>", unsafe_allow_html=True
    )
    st.markdown(
        "<p class='subtitle'>Your intelligent AI assistant powered by Agno</p>",
        unsafe_allow_html=True,
    )

    ####################################################################
    # Model selector
    ####################################################################
    model_options = {
        "gpt-4o": "openai:gpt-4o",
        "gemini-2.0-flash-exp": "google:gemini-2.0-flash-exp",
        "claude-3-5-sonnet": "anthropic:claude-3-5-sonnet-20241022",
    }
    selected_model = st.sidebar.selectbox(
        "Select a model",
        options=list(model_options.keys()),
        index=0,
        key="model_selector",
    )
    model_id = model_options[selected_model]

    ####################################################################
    # Sidebar
    ####################################################################
    sidebar_widget()

    ####################################################################
    # Initialize Agent
    ####################################################################
    uagi: Agent
    if (
        "uagi" not in st.session_state
        or st.session_state["uagi"] is None
        or st.session_state.get("current_model") != model_id
    ):
        uagi = get_uagi(
            model_id=model_id,
            # Pull tools from session state
            calculator=st.session_state.get("calculator_enabled", True),
            ddg_search=st.session_state.get("ddg_search_enabled", True),
            shell_tools=st.session_state.get("shell_tools_enabled", False),
            file_tools=st.session_state.get("file_tools_enabled", True),
            # Pull team members from session state
            data_analyst=st.session_state.get("data_analyst_enabled", False),
            python_agent=st.session_state.get("python_agent_enabled", False),
            research_agent=st.session_state.get("research_agent_enabled", False),
            investment_agent=st.session_state.get("investment_agent_enabled", False),
        )
        st.session_state["uagi"] = uagi
        st.session_state["current_model"] = model_id
    else:
        uagi = st.session_state["uagi"]

    ####################################################################
    # Load Agent Session from the database
    ####################################################################
    try:
        st.session_state["uagi_session_id"] = uagi.load_session()
    except Exception:
        st.warning("Could not create Agent session, is the database running?")
        return

    ####################################################################
    # Session manager
    ####################################################################
    session_manager(uagi, model_id)

    ####################################################################
    # Knowledge manager
    ####################################################################
    knowledge_manager(uagi)

    ####################################################################
    # About section
    ####################################################################
    about_widget()

    ####################################################################
    # Load runs from memory
    ####################################################################
    agent_runs = uagi.memory.runs
    if len(agent_runs) > 0:
        logger.debug("Loading run history")
        st.session_state["messages"] = []
        for _run in agent_runs:
            if _run.message is not None:
                add_message(_run.message.role, _run.message.content)
            if _run.response is not None:
                add_message("assistant", _run.response.content, _run.response.tools)
    else:
        logger.debug("No run history found")
        st.session_state["messages"] = []

    ####################################################################
    # Get user input
    ####################################################################
    if prompt := st.chat_input("👋 How can I help?"):
        add_message("user", prompt)

    ####################################################################
    # Display chat history
    ####################################################################
    for message in st.session_state["messages"]:
        if message["role"] in ["user", "assistant"]:
            _content = message["content"]
            if _content is not None:
                with st.chat_message(message["role"]):
                    # Display tool calls if they exist in the message
                    if "tool_calls" in message and message["tool_calls"]:
                        display_tool_calls(st.empty(), message["tool_calls"])
                    st.markdown(_content)

    ####################################################################
    # Generate response for user message
    ####################################################################
    last_message = (
        st.session_state["messages"][-1] if st.session_state["messages"] else None
    )
    if last_message and last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            # Create container for tool calls
            tool_calls_container = st.empty()
            resp_container = st.empty()
            with st.spinner("🤔 Thinking..."):
                response = ""
                try:
                    # Run the agent and stream the response
                    run_response = uagi.run(question, stream=True)
                    for _resp_chunk in run_response:
                        # Display tool calls if available
                        if _resp_chunk.tools and len(_resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, _resp_chunk.tools)

                        # Display response
                        if _resp_chunk.content is not None:
                            response += _resp_chunk.content
                            resp_container.markdown(response)

                    add_message("assistant", response, uagi.run_response.tools)
                except Exception as e:
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    add_message("assistant", error_message)
                    st.error(error_message)


if __name__ == "__main__":
    main()
