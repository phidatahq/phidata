from typing import List
import nest_asyncio
import streamlit as st
from agno.agent import Agent
from agno.document import Document
from agno.document.reader.website_reader import WebsiteReader
from agno.document.reader.pdf_reader import PDFReader
from agno.document.reader.text_reader import TextReader
from agno.document.reader.csv_reader import CSVReader
from agno.utils.log import logger
from agentic_rag import get_agentic_rag_agent
from utils import (
    CUSTOM_CSS,
    add_message,
    display_tool_calls,
    sidebar_widget,
    session_selector_widget,
    rename_session_widget,
    about_widget,
)

nest_asyncio.apply()
st.set_page_config(
    page_title="Agentic RAG",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Add custom CSS


def restart_agent():
    """Restart the agent and reset session state."""
    logger.debug("---*--- Restarting Agent ---*---")
    for key in ["agentic_rag_agent", "agentic_rag_agent_session_id", "messages"]:
        st.session_state.pop(key, None)
    st.session_state["url_scrape_key"] = st.session_state.get("url_scrape_key", 0) + 1
    st.session_state["file_uploader_key"] = st.session_state.get("file_uploader_key", 100) + 1
    st.rerun()


def get_reader(file_type: str):
    """Return appropriate reader based on file type."""
    readers = {
        "pdf": PDFReader(),
        "csv": CSVReader(),
        "txt": TextReader(),
    }
    return readers.get(file_type.lower(), None)


def initialize_agent(model_id: str):
    """Initialize or retrieve the AutoRAG agent."""
    if "agentic_rag_agent" not in st.session_state or st.session_state["agentic_rag_agent"] is None:
        logger.info(f"---*--- Creating {model_id} Agent ---*---")
        agent: Agent = get_agentic_rag_agent(
            model_id=model_id, session_id=st.session_state.get("agentic_rag_agent_session_id")
        )
        st.session_state["agentic_rag_agent"] = agent
        st.session_state["agentic_rag_agent_session_id"] = agent.session_id
    return st.session_state["agentic_rag_agent"]


def main():
    ####################################################################
    # App header
    ####################################################################
    st.markdown("<h1 class='main-title'>Agentic RAG </h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Your intelligent research assistant powered by Agno</p>",
        unsafe_allow_html=True,
    )

    ####################################################################
    # Model selector
    ####################################################################
    model_options = {
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
    }
    selected_model = st.sidebar.selectbox(
        "Select a model",
        options=list(model_options.keys()),
        index=0,
        key="model_selector",
    )
    model_id = model_options[selected_model]

    ####################################################################
    # Initialize Agent
    ####################################################################
    agentic_rag_agent: Agent
    if (
        "agentic_rag_agent" not in st.session_state
        or st.session_state["agentic_rag_agent"] is None
        or st.session_state.get("current_model") != model_id
    ):
        logger.info("---*--- Creating new Auto RAG agent ---*---")
        agentic_rag_agent = get_agentic_rag_agent(model_id=model_id)
        st.session_state["agentic_rag_agent"] = agentic_rag_agent
        st.session_state["current_model"] = model_id
    else:
        agentic_rag_agent = st.session_state["agentic_rag_agent"]

    ####################################################################
    # Load Agent Session from the database
    ####################################################################
    try:
        st.session_state["agentic_rag_agent_session_id"] = agentic_rag_agent.load_session()
    except Exception:
        st.warning("Could not create Agent session, is the database running?")
        return

    ####################################################################
    # Load runs from memory
    ####################################################################
    agent_runs = agentic_rag_agent.memory.runs
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
    # Sidebar
    ####################################################################
            
    st.sidebar.markdown("#### 📚 Document Management")
    input_url = st.sidebar.text_input("Add URL to Knowledge Base")
    if input_url:  # Check if the user has entered a URL
        alert = st.sidebar.info("Processing URLs...", icon="ℹ️")
        scraper = WebsiteReader(max_links=2, max_depth=1)
        docs: List[Document] = scraper.read(input_url)
        if docs:
            agentic_rag_agent.knowledge.load_documents(docs, upsert=True)
            st.sidebar.success("URL added to knowledge base")
        else:
            st.sidebar.error("Could not process the provided URL")
        alert.empty()

    uploaded_file = st.sidebar.file_uploader("Add a Document (.pdf, .csv, or .txt)", key="file_upload")
    if uploaded_file:
        file_type = uploaded_file.name.split(".")[-1].lower()
        reader = get_reader(file_type)
        if reader:
            docs = reader.read(uploaded_file)
            agentic_rag_agent.knowledge.load_documents(docs, upsert=True)

    if st.sidebar.button("Clear Knowledge Base"):
        agentic_rag_agent.knowledge.vector_db.delete()
        st.sidebar.success("Knowledge base cleared")

    sidebar_widget()

    ####################################################################
      ####################################################################
    if prompt := st.chat_input("👋 Ask me anything!"):
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
                    run_response = agentic_rag_agent.run(question, stream=True)
                    for _resp_chunk in run_response:
                        # Display tool calls if available
                        if _resp_chunk.tools and len(_resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, _resp_chunk.tools)

                        # Display response
                        if _resp_chunk.content is not None:
                            response += _resp_chunk.content
                            resp_container.markdown(response)

                    add_message("assistant", response, agentic_rag_agent.run_response.tools)
                except Exception as e:
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    add_message("assistant", error_message)
                    st.error(error_message)

    ####################################################################
    # Session selector
    ####################################################################
    session_selector_widget(agentic_rag_agent, model_id)
    rename_session_widget(agentic_rag_agent)

    ####################################################################
    # About section
    ####################################################################
    about_widget()


main()
