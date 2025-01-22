from typing import List
import nest_asyncio
import streamlit as st
from phi.agent import Agent
from phi.document import Document
from phi.document.reader.website import WebsiteReader
from phi.document.reader.pdf import PDFReader
from phi.document.reader.text import TextReader
from phi.document.reader.csv_reader import CSVReader
from phi.utils.log import logger
from cookbook.examples.streamlit.agentic_rag.agentic_rag_flow import get_auto_rag_agent

nest_asyncio.apply()
st.set_page_config(
    page_title="Autonomous RAG",
    page_icon=":orange_heart:",
)
st.title("Autonomous RAG")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def restart_agent():
    """Restart the agent and reset session state."""
    logger.debug("---*--- Restarting Agent ---*---")
    for key in ["auto_rag_agent", "auto_rag_agent_session_id", "messages"]:
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
    if "auto_rag_agent" not in st.session_state or st.session_state["auto_rag_agent"] is None:
        logger.info(f"---*--- Creating {model_id} Agent ---*---")
        agent: Agent = get_auto_rag_agent(
            model_id=model_id, session_id=st.session_state.get("auto_rag_agent_session_id")
        )
        st.session_state["auto_rag_agent"] = agent
        st.session_state["auto_rag_agent_session_id"] = agent.session_id
    return st.session_state["auto_rag_agent"]


def main():
    """Main function to run the Streamlit app."""
    # Select LLM model
    model_id = st.sidebar.selectbox("Select LLM", options=["gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"])
    if st.session_state.get("model_id") != model_id:
        st.session_state["model_id"] = model_id
        restart_agent()

    # Initialize the agent
    auto_rag_agent = initialize_agent(model_id)

    # Load chat history from memory
    if auto_rag_agent.memory and not st.session_state["messages"]:
        logger.debug("Loading chat history")
        st.session_state["messages"] = [
            {"role": message.role, "content": message.content} for message in auto_rag_agent.memory.messages
        ]
    elif not st.session_state["messages"]:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "agent", "content": "Upload a doc and ask me questions..."}]

    # Handle user input and generate responses
    if prompt := st.chat_input("Ask a question:"):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("agent"):
            agent_response = auto_rag_agent.run(prompt)
            st.session_state["messages"].append({"role": "agent", "content": agent_response.content})

    # Display chat history
    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Add websites to the knowledge base
    input_url = st.sidebar.text_input("Add URL to Knowledge Base")
    if input_url:  # Check if the user has entered a URL
        alert = st.sidebar.info("Processing URLs...", icon="ℹ️")
        scraper = WebsiteReader(max_links=2, max_depth=1)
        docs: List[Document] = scraper.read(input_url)
        if docs:
            auto_rag_agent.knowledge.load_documents(docs, upsert=True)
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
            auto_rag_agent.knowledge.load_documents(docs, upsert=True)

    if st.sidebar.button("Clear Knowledge Base"):
        auto_rag_agent.knowledge.vector_db.delete()
        st.sidebar.success("Knowledge base cleared")

    # Session Management
    if auto_rag_agent.storage:
        session_ids = auto_rag_agent.storage.get_all_session_ids()
        new_session_id = st.sidebar.selectbox("Session ID", options=session_ids)  # type: ignore
        if new_session_id != st.session_state.get("auto_rag_agent_session_id"):
            st.session_state["auto_rag_agent"] = get_auto_rag_agent(model_id=model_id, session_id=new_session_id)
            st.session_state["auto_rag_agent_session_id"] = new_session_id
            st.rerun()

    if st.sidebar.button("New Run"):
        restart_agent()

    if "embeddings_model_updated" in st.session_state:
        st.sidebar.info("Please add documents again as the embeddings model has changed.")
        st.session_state["embeddings_model_updated"] = False


main()
