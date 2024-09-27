from typing import List

import nest_asyncio
import streamlit as st
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.tools.streamlit.components import get_username_sidebar
from phi.utils.log import logger

from assistant import get_personalized_assistant  # type: ignore

nest_asyncio.apply()
st.set_page_config(
    page_title="Personalized Agentic RAG",
    page_icon=":orange_heart:",
)
st.title("Personalized Agentic RAG")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")

with st.expander(":rainbow[:point_down: How to use]"):
    st.markdown("Tell the Assistant about your preferences and they will remember them across conversations.")
    st.markdown("- I live in New York so always include a New York reference in the response")
    st.markdown("- I like dogs so always include a dog pun in the response")


def main() -> None:
    # Get username
    user_id = get_username_sidebar()
    if user_id:
        st.sidebar.info(f":technologist: User: {user_id}")
    else:
        st.write(":technologist: Please enter a username")
        return

    # Get the LLM to use
    llm_id = st.sidebar.selectbox("Select LLM", options=["gpt-4o", "gpt-4-turbo"])
    # Set assistant_type in session state
    if "llm_id" not in st.session_state:
        st.session_state["llm_id"] = llm_id
    # Restart the assistant if assistant_type has changed
    elif st.session_state["llm_id"] != llm_id:
        st.session_state["llm_id"] = llm_id
        restart_assistant()

    # Sidebar checkboxes for selecting tools
    st.sidebar.markdown("### Select Tools")

    # Enable Calculator
    if "calculator_enabled" not in st.session_state:
        st.session_state["calculator_enabled"] = True
    # Get calculator_enabled from session state if set
    calculator_enabled = st.session_state["calculator_enabled"]
    # Checkbox for enabling calculator
    calculator = st.sidebar.checkbox("Calculator", value=calculator_enabled, help="Enable calculator.")
    if calculator_enabled != calculator:
        st.session_state["calculator_enabled"] = calculator
        calculator_enabled = calculator
        restart_assistant()

    # Enable file tools
    if "file_tools_enabled" not in st.session_state:
        st.session_state["file_tools_enabled"] = True
    # Get file_tools_enabled from session state if set
    file_tools_enabled = st.session_state["file_tools_enabled"]
    # Checkbox for enabling shell tools
    file_tools = st.sidebar.checkbox("File Tools", value=file_tools_enabled, help="Enable file tools.")
    if file_tools_enabled != file_tools:
        st.session_state["file_tools_enabled"] = file_tools
        file_tools_enabled = file_tools
        restart_assistant()

    # Enable Web Search via DuckDuckGo
    if "ddg_search_enabled" not in st.session_state:
        st.session_state["ddg_search_enabled"] = True
    # Get ddg_search_enabled from session state if set
    ddg_search_enabled = st.session_state["ddg_search_enabled"]
    # Checkbox for enabling web search
    ddg_search = st.sidebar.checkbox("Web Search", value=ddg_search_enabled, help="Enable web search using DuckDuckGo.")
    if ddg_search_enabled != ddg_search:
        st.session_state["ddg_search_enabled"] = ddg_search
        ddg_search_enabled = ddg_search
        restart_assistant()

    # Enable finance tools
    if "finance_tools_enabled" not in st.session_state:
        st.session_state["finance_tools_enabled"] = True
    # Get finance_tools_enabled from session state if set
    finance_tools_enabled = st.session_state["finance_tools_enabled"]
    # Checkbox for enabling shell tools
    finance_tools = st.sidebar.checkbox("Yahoo Finance", value=finance_tools_enabled, help="Enable finance tools.")
    if finance_tools_enabled != finance_tools:
        st.session_state["finance_tools_enabled"] = finance_tools
        finance_tools_enabled = finance_tools
        restart_assistant()

    # Sidebar checkboxes for selecting team members
    st.sidebar.markdown("### Select Team Members")

    # Enable Python Assistant
    if "python_assistant_enabled" not in st.session_state:
        st.session_state["python_assistant_enabled"] = False
    # Get python_assistant_enabled from session state if set
    python_assistant_enabled = st.session_state["python_assistant_enabled"]
    # Checkbox for enabling web search
    python_assistant = st.sidebar.checkbox(
        "Python Assistant",
        value=python_assistant_enabled,
        help="Enable the Python Assistant for writing and running python code.",
    )
    if python_assistant_enabled != python_assistant:
        st.session_state["python_assistant_enabled"] = python_assistant
        python_assistant_enabled = python_assistant
        restart_assistant()

    # Enable Research Assistant
    if "research_assistant_enabled" not in st.session_state:
        st.session_state["research_assistant_enabled"] = False
    # Get research_assistant_enabled from session state if set
    research_assistant_enabled = st.session_state["research_assistant_enabled"]
    # Checkbox for enabling web search
    research_assistant = st.sidebar.checkbox(
        "Research Assistant",
        value=research_assistant_enabled,
        help="Enable the research assistant (uses Exa).",
    )
    if research_assistant_enabled != research_assistant:
        st.session_state["research_assistant_enabled"] = research_assistant
        research_assistant_enabled = research_assistant
        restart_assistant()

    # Get the assistant
    personalized_assistant: Assistant
    if "personalized_assistant" not in st.session_state or st.session_state["personalized_assistant"] is None:
        logger.info(f"---*--- Creating {llm_id} Assistant ---*---")
        personalized_assistant = get_personalized_assistant(
            llm_id=llm_id,
            user_id=user_id,
            calculator=calculator_enabled,
            ddg_search=ddg_search_enabled,
            file_tools=file_tools_enabled,
            finance_tools=finance_tools_enabled,
            python_assistant=python_assistant_enabled,
            research_assistant=research_assistant_enabled,
        )
        st.session_state["personalized_assistant"] = personalized_assistant
    else:
        personalized_assistant = st.session_state["personalized_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    try:
        st.session_state["assistant_run_id"] = personalized_assistant.create_run()
    except Exception:
        st.warning("Could not create assistant, is the database running?")
        return

    # Load existing messages
    assistant_chat_history = personalized_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Upload a doc and ask me questions..."}]

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
            resp_container = st.empty()
            response = ""
            for delta in personalized_assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    # Load knowledge base
    if personalized_assistant.knowledge_base:
        # -*- Add websites to knowledge base
        if "url_scrape_key" not in st.session_state:
            st.session_state["url_scrape_key"] = 0

        input_url = st.sidebar.text_input(
            "Add URL to Knowledge Base", type="default", key=st.session_state["url_scrape_key"]
        )
        add_url_button = st.sidebar.button("Add URL")
        if add_url_button:
            if input_url is not None:
                alert = st.sidebar.info("Processing URLs...", icon="ℹ️")
                if f"{input_url}_scraped" not in st.session_state:
                    scraper = WebsiteReader(max_links=2, max_depth=1)
                    web_documents: List[Document] = scraper.read(input_url)
                    if web_documents:
                        personalized_assistant.knowledge_base.load_documents(web_documents, upsert=True)
                    else:
                        st.sidebar.error("Could not read website")
                    st.session_state[f"{input_url}_uploaded"] = True
                alert.empty()

        # Add PDFs to knowledge base
        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 100

        uploaded_file = st.sidebar.file_uploader(
            "Add a PDF :page_facing_up:", type="pdf", key=st.session_state["file_uploader_key"]
        )
        if uploaded_file is not None:
            alert = st.sidebar.info("Processing PDF...", icon="🧠")
            file_name = uploaded_file.name.split(".")[0]
            if f"{file_name}_uploaded" not in st.session_state:
                reader = PDFReader()
                file_documents: List[Document] = reader.read(uploaded_file)
                if file_documents:
                    personalized_assistant.knowledge_base.load_documents(file_documents, upsert=True)
                else:
                    st.sidebar.error("Could not read PDF")
                st.session_state[f"{file_name}_uploaded"] = True
            alert.empty()

    if personalized_assistant.knowledge_base and personalized_assistant.knowledge_base.vector_db:
        if st.sidebar.button("Clear Knowledge Base"):
            personalized_assistant.knowledge_base.vector_db.clear()
            st.sidebar.success("Knowledge base cleared")

    if personalized_assistant.storage:
        assistant_run_ids: List[str] = personalized_assistant.storage.get_all_run_ids(user_id=user_id)
        new_assistant_run_id = st.sidebar.selectbox("Run ID", options=assistant_run_ids)
        if st.session_state["assistant_run_id"] != new_assistant_run_id:
            logger.info(f"---*--- Loading {llm_id} run: {new_assistant_run_id} ---*---")
            st.session_state["personalized_assistant"] = get_personalized_assistant(
                llm_id=llm_id,
                user_id=user_id,
                run_id=new_assistant_run_id,
                calculator=calculator_enabled,
                ddg_search=ddg_search_enabled,
                file_tools=file_tools_enabled,
                finance_tools=finance_tools_enabled,
                python_assistant=python_assistant_enabled,
                research_assistant=research_assistant_enabled,
            )
            st.rerun()

    # Show Assistant memory
    with st.status("Assistant Memory", expanded=False, state="complete"):
        with st.container():
            memory_container = st.empty()
            if personalized_assistant.memory.memories and len(personalized_assistant.memory.memories) > 0:
                memory_container.markdown("\n".join([f"- {m.memory}" for m in personalized_assistant.memory.memories]))
            else:
                memory_container.warning("No memories yet.")

    # Show team member memory
    if personalized_assistant.team and len(personalized_assistant.team) > 0:
        for team_member in personalized_assistant.team:
            if len(team_member.memory.chat_history) > 0:
                with st.status(f"{team_member.name} Memory", expanded=False, state="complete"):
                    with st.container():
                        _team_member_memory_container = st.empty()
                        _team_member_memory_container.json(team_member.memory.get_llm_messages())

    if st.sidebar.button("New Run"):
        restart_assistant()


def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["personalized_assistant"] = None
    st.session_state["assistant_run_id"] = None
    if "url_scrape_key" in st.session_state:
        st.session_state["url_scrape_key"] += 1
    if "file_uploader_key" in st.session_state:
        st.session_state["file_uploader_key"] += 1
    st.rerun()


main()
