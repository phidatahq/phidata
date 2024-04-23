import streamlit as st
from phi.assistant import Assistant
from phi.utils.log import logger

from assistant import get_autonomous_assistant  # type: ignore

st.set_page_config(
    page_title="Local Function Calling",
    page_icon=":orange_heart:",
)
st.title("Local Function Calling with Ollama")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    st.session_state["auto_assistant"] = None


def main() -> None:
    # Get model
    llm_model = st.sidebar.selectbox("Select Model", options=["llama3", "phi3", "openhermes"])
    # Set assistant_type in session state
    if "llm_model" not in st.session_state:
        st.session_state["llm_model"] = llm_model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["llm_model"] != llm_model:
        st.session_state["llm_model"] = llm_model
        restart_assistant()

    # Sidebar checkboxes for selecting tools
    st.sidebar.markdown("### Select Tools")
    st.session_state["selected_tools"] = []
    yfinance = st.sidebar.checkbox("YFinance", value=True, on_change=restart_assistant)
    tavily_rearch = st.sidebar.checkbox("Tavily Search", value=False, on_change=restart_assistant)

    # Get the assistant
    auto_assistant: Assistant
    if "auto_assistant" not in st.session_state or st.session_state["auto_assistant"] is None:
        logger.info(f"---*--- Creating {llm_model} Assistant ---*---")
        auto_assistant = get_autonomous_assistant(
            llm_model=llm_model,
            tavily_search=tavily_rearch,
            yfinance=yfinance,
        )
        st.session_state["auto_assistant"] = auto_assistant
    else:
        auto_assistant = st.session_state["auto_assistant"]

    # Load existing messages
    assistant_chat_history = auto_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me questions..."}]

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
            for delta in auto_assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    if st.sidebar.button("New Run"):
        restart_assistant()


main()
