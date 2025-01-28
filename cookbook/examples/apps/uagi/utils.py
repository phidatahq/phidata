from typing import Any, Dict, List, Optional

import streamlit as st
from agents import get_uagi
from agno.agent.agent import Agent
from agno.document import Document
from agno.document.reader.pdf_reader import PDFReader
from agno.document.reader.website_reader import WebsiteReader
from agno.utils.log import logger


def load_agent_knowledge():
    """Load Agent knowledge base if not already done"""
    from load_knowledge import load_agent_knowledge

    if "agent_knowledge_loaded" not in st.session_state:
        with st.spinner("📚 Loading Agent knowledge..."):
            load_agent_knowledge()
        st.session_state["agent_knowledge_loaded"] = True
        st.success("✅ Agent knowledge loaded successfully!")


def add_message(
    role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None
) -> None:
    """Safely add a message to the session state"""
    if "messages" not in st.session_state or not isinstance(
        st.session_state["messages"], list
    ):
        st.session_state["messages"] = []
    st.session_state["messages"].append(
        {"role": role, "content": content, "tool_calls": tool_calls}
    )


def restart_agent():
    """Reset the agent and clear chat history"""
    logger.debug("---*--- Restarting agent ---*---")
    st.session_state["uagi"] = None
    st.session_state["uagi_session_id"] = None
    st.session_state["messages"] = []
    st.session_state["url_scrape_key"] = st.session_state.get("url_scrape_key", 0) + 1
    st.session_state["file_uploader_key"] = (
        st.session_state.get("file_uploader_key", 100) + 1
    )
    st.rerun()


def export_chat_history():
    """Export chat history as markdown"""
    if "messages" in st.session_state:
        chat_text = "# UAGI - Chat History\n\n"
        for msg in st.session_state["messages"]:
            role = "🤖 Assistant" if msg["role"] == "agent" else "👤 User"
            chat_text += f"### {role}\n{msg['content']}\n\n"
        return chat_text
    return ""


def display_tool_calls(tool_calls_container, tools):
    """Display tool calls in a streamlit container with expandable sections.

    Args:
        tool_calls_container: Streamlit container to display the tool calls
        tools: List of tool call dictionaries containing name, args, content, and metrics
    """
    with tool_calls_container.container():
        for tool_call in tools:
            _tool_name = tool_call.get("tool_name")
            _tool_args = tool_call.get("tool_args")
            _content = tool_call.get("content")
            _metrics = tool_call.get("metrics")

            with st.expander(
                f"🛠️ {_tool_name.replace('_', ' ').title()}", expanded=False
            ):
                if isinstance(_tool_args, dict) and "query" in _tool_args:
                    st.code(_tool_args["query"], language="sql")

                if _tool_args and _tool_args != {"query": None}:
                    st.markdown("**Arguments:**")
                    st.json(_tool_args)

                if _content:
                    st.markdown("**Results:**")
                    try:
                        st.json(_content)
                    except Exception as e:
                        st.markdown(_content)

                if _metrics:
                    st.markdown("**Metrics:**")
                    st.json(_metrics)


def sidebar_widget() -> None:
    """Display a sidebar with sample user queries"""
    with st.sidebar:
        st.markdown("### ⚙️ Tools")
        tools_container = st.container()
        with tools_container:
            col1, col2 = st.columns(2)
            with col1:
                st.checkbox(
                    "File Manager",
                    value=st.session_state.get("file_manager_enabled", True),
                    key="file_manager_enabled",
                )
                st.checkbox(
                    "Shell Tools",
                    value=st.session_state.get("shell_tools_enabled", True),
                    key="shell_tools_enabled",
                )
            with col2:
                st.checkbox(
                    "Image Gen",
                    value=st.session_state.get("image_generation_enabled", True),
                    key="image_generation_enabled",
                )
                st.checkbox(
                    "Post to X",
                    value=st.session_state.get("twitter_post_enabled", True),
                    key="twitter_post_enabled",
                )

        st.markdown("### 👨‍🚀 Team Members")
        agents_container = st.container()
        with agents_container:
            st.checkbox(
                "Research Agent",
                value=st.session_state.get("research_agent_enabled", True),
                key="research_agent_enabled",
            )
            st.checkbox(
                "Movie Recommender",
                value=st.session_state.get("movie_recommender_enabled", True),
                key="movie_recommender_enabled",
            )
            st.checkbox(
                "Video Summaries",
                value=st.session_state.get("video_summaries_enabled", True),
                key="video_summaries_enabled",
            )
            st.checkbox(
                "Travel Planner",
                value=st.session_state.get("travel_planner_enabled", True),
                key="travel_planner_enabled",
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
                file_name="uagi_chat_history.md",
                mime="text/markdown",
            ):
                st.success("Chat history exported!")

        if st.sidebar.button("🚀 Load Knowledge"):
            load_agent_knowledge()


def session_manager(agent: Agent, model_id: str) -> None:
    """Display session management widgets in the sidebar"""
    if not agent.storage:
        return

    # Get all sessions and prepare options
    agent_sessions = agent.storage.get_all_sessions()
    session_options = []
    for session in agent_sessions:
        session_id = session.session_id
        session_name = (
            session.session_data.get("session_name", None)
            if session.session_data
            else None
        )
        display_name = session_name if session_name else session_id
        session_options.append({"id": session_id, "display": display_name})

    # Session selector
    st.sidebar.markdown("### 🌟 Sessions")
    selected_session = st.sidebar.selectbox(
        "Session",
        options=[s["display"] for s in session_options],
        key="session_selector",
        label_visibility="collapsed",
    )
    selected_session_id = next(
        s["id"] for s in session_options if s["display"] == selected_session
    )

    # Session rename interface
    container = st.sidebar.container()
    session_row = container.columns([3, 1], vertical_alignment="center")

    # Initialize session_edit_mode if needed
    if "session_edit_mode" not in st.session_state:
        st.session_state.session_edit_mode = False

    with session_row[0]:
        if st.session_state.session_edit_mode:
            new_session_name = st.text_input(
                "Session Name",
                value=agent.session_name,
                key="session_name_input",
                label_visibility="collapsed",
            )
        else:
            st.markdown(f"Session Name: **{agent.session_name}**")

    with session_row[1]:
        if st.session_state.session_edit_mode:
            if st.button("✓", key="save_session_name", type="primary"):
                if new_session_name:
                    agent.rename_session(new_session_name)
                    st.session_state.session_edit_mode = False
                    container.success("Renamed!")
                    st.rerun()  # Refresh to update the session selector
        else:
            if st.button("✎", key="edit_session_name"):
                st.session_state.session_edit_mode = True

    # Handle session switching
    if st.session_state["uagi_session_id"] != selected_session_id:
        logger.info(f"---*--- Loading {model_id} run: {selected_session_id} ---*---")
        st.session_state["uagi"] = get_uagi(
            model_id=model_id,
            session_id=selected_session_id,
        )
        st.rerun()


def knowledge_manager(agent: Agent) -> None:
    """Display a knowledge base manager in the sidebar"""

    if agent.knowledge:
        st.sidebar.markdown("### 📚 Knowledge Base")
        kb_container = st.sidebar.container()

        with kb_container:
            # # Display existing knowledge sources
            # if agent.knowledge.vector_db:
            #     knowledge_sources = agent.knowledge.vector_db.get_all_sources()
            #     if knowledge_sources:
            #         source_options = []
            #         for source in knowledge_sources:
            #             source_id = source.source_id
            #             source_name = (
            #                 source.metadata.get("source_name", None)
            #                 if source.metadata
            #                 else None
            #             )
            #             display_name = source_name if source_name else source_id
            #             source_options.append({"id": source_id, "display": display_name})

            #         # Display source selector
            #         st.sidebar.selectbox(
            #             "Sources",
            #             options=[s["display"] for s in source_options],
            #             key="knowledge_source_selector",
            #         )

            # URL Input
            url_col1, url_col2 = st.columns([3, 1], vertical_alignment="center")
            input_url = None
            with url_col1:
                input_url = st.text_input(
                    "Add URL",
                    key=st.session_state.get("url_scrape_key", 0),
                    placeholder="Enter URL to scrape...",
                    label_visibility="collapsed",
                )
            with url_col2:
                add_url = st.button("Add", key="add_url_btn")
                if add_url:
                    if input_url is not None:
                        alert = st.sidebar.info("Reading URLs...", icon="ℹ️")
                        if f"{input_url}_scraped" not in st.session_state:
                            scraper = WebsiteReader(max_links=2, max_depth=1)
                            web_documents: List[Document] = scraper.read(input_url)
                            if web_documents:
                                agent.knowledge.load_documents(
                                    web_documents, upsert=True
                                )
                            else:
                                st.sidebar.error("Could not read website")
                            st.session_state[f"{input_url}_uploaded"] = True
                        alert.empty()

            # File Upload
            uploaded_file = st.file_uploader(
                "Upload PDF",
                type="pdf",
                key=st.session_state.get("file_uploader_key", 100),
                help="Upload PDF documents to knowledge base",
            )
            if uploaded_file is not None:
                alert = st.sidebar.info("Processing PDF...", icon="🧠")
                _file_name = uploaded_file.name.split(".")[0]
                if f"{_file_name}_uploaded" not in st.session_state:
                    reader = PDFReader()
                    docs_in_file: List[Document] = reader.read(uploaded_file)
                    if docs_in_file:
                        agent.knowledge.load_documents(docs_in_file, upsert=True)
                    else:
                        st.sidebar.error("Could not read PDF")
                    st.session_state[f"{_file_name}_uploaded"] = True
                alert.empty()

            # Clear Knowledge Base
            if st.button("Clear Knowledge Base", type="secondary"):
                if agent.knowledge.vector_db:
                    agent.knowledge.vector_db.delete()
                    st.success("Knowledge base cleared!")


def display_team_memory(agent: Agent) -> None:
    """Display memory contents for each team member in the sidebar."""
    # Show team member memory
    if agent.team and len(agent.team) > 0:
        for team_member in agent.team:
            if team_member.memory and len(team_member.memory.messages) > 0:
                with st.status(
                    f"{team_member.name} Memory", expanded=False, state="complete"
                ):
                    with st.container():
                        _team_member_memory_container = st.empty()
                        _team_member_memory_container.json(
                            team_member.memory.get_messages()
                        )


def about_widget() -> None:
    """Display an about section in the sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("""Welcome to your Universal Agent Interface!

    I can help you with:
    🔬 Research & Analysis
    🌐 Web Search & Information
    🎬 Movie Recommendations
    📺 Youtube video summaries
    ✈️ Travel Planning
    ⚙️ System Operations

    Built with:
    - 🚀 Agno
    - 💫 Streamlit
    """)


CUSTOM_CSS = """
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
"""
