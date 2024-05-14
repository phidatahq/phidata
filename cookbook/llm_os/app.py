from pathlib import Path
from typing import List

import nest_asyncio
import streamlit as st
import json
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.tools.csv_tools import CsvTools
from phi.utils.log import logger

from assistant import get_llm_os  # type: ignore

nest_asyncio.apply()

cwd = Path(__file__).parent.resolve()
scratch_dir = cwd.joinpath("scratch")
if not scratch_dir.exists():
    scratch_dir.mkdir(exist_ok=True, parents=True)

st.set_page_config(
    page_title="LLM OS",
    page_icon=":orange_heart:",
)
st.title("LLM OS")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def main() -> None:
    # Get LLM Model
    llm_id = st.sidebar.selectbox("Select LLM", options=["gpt-4o", "gpt-4-turbo"]) or "gpt-4o"
    # Set llm_id in session state
    if "llm_id" not in st.session_state:
        st.session_state["llm_id"] = llm_id
    # Restart the assistant if llm_id changes
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

    # Enable Yahoo Finance Tools
    if "yfinance_tools_enabled" not in st.session_state:
        st.session_state["yfinance_tools_enabled"] = False
    # Get yfinance_tools_enabled from session state if set
    yfinance_tools_enabled = st.session_state["yfinance_tools_enabled"]
    # Checkbox for enabling Yahoo Finance tools
    yfinance_tools = st.sidebar.checkbox("Yahoo Finance Tools", value=yfinance_tools_enabled, help="Enable Yahoo Finance tools.")
    if yfinance_tools_enabled != yfinance_tools:
        st.session_state["yfinance_tools_enabled"] = yfinance_tools
        yfinance_tools_enabled = yfinance_tools
        restart_assistant()
    if "csv_tools_enabled" not in st.session_state:
        st.session_state["csv_tools_enabled"] = False
    # Get csv_tools_enabled from session state if set
    csv_tools_enabled = st.session_state["csv_tools_enabled"]
    # Checkbox for enabling CSV tools
    csv_tools = st.sidebar.checkbox("CSV Tools", value=csv_tools_enabled, help="Enable CSV tools.")
    if csv_tools_enabled != csv_tools:
        st.session_state["csv_tools_enabled"] = csv_tools
        csv_tools_enabled = csv_tools
        restart_assistant()
    if "shell_tools_enabled" not in st.session_state:
        st.session_state["shell_tools_enabled"] = False
    # Get shell_tools_enabled from session state if set
    shell_tools_enabled = st.session_state["shell_tools_enabled"]
    # Checkbox for enabling shell tools
    shell_tools = st.sidebar.checkbox("Shell Tools", value=shell_tools_enabled, help="Enable shell tools.")
    if shell_tools_enabled != shell_tools:
        st.session_state["shell_tools_enabled"] = shell_tools
        shell_tools_enabled = shell_tools
        restart_assistant()

    # Sidebar checkboxes for selecting team members
    st.sidebar.markdown("### Select Team Members")

    # Enable Data Analyst
    if "data_analyst_enabled" not in st.session_state:
        st.session_state["data_analyst_enabled"] = False
    # Get data_analyst_enabled from session state if set
    data_analyst_enabled = st.session_state["data_analyst_enabled"]
    # Checkbox for enabling web search
    data_analyst = st.sidebar.checkbox(
        "Data Analyst",
        value=data_analyst_enabled,
        help="Enable the Data Analyst assistant for data related queries.",
    )
    if data_analyst_enabled != data_analyst:
        st.session_state["data_analyst_enabled"] = data_analyst
        data_analyst_enabled = data_analyst
        restart_assistant()

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

    # Enable Investment Assistant
    if "investment_assistant_enabled" not in st.session_state:
        st.session_state["investment_assistant_enabled"] = False
    # Get investment_assistant_enabled from session state if set
    investment_assistant_enabled = st.session_state["investment_assistant_enabled"]
    # Checkbox for enabling web search
    investment_assistant = st.sidebar.checkbox(
        "Investment Assistant",
        value=investment_assistant_enabled,
        help="Enable the investment assistant. NOTE: This is not financial advice.",
    )
    if investment_assistant_enabled != investment_assistant:
        st.session_state["investment_assistant_enabled"] = investment_assistant
        investment_assistant_enabled = investment_assistant
        restart_assistant()

    # Ensure the total number of tools does not exceed the maximum allowed length of 128
    max_tools = 128
    selected_tools = [
        calculator_enabled,
        ddg_search_enabled,
        file_tools_enabled,
        csv_tools_enabled,
        shell_tools_enabled,
        yfinance_tools_enabled,
    ]
    if sum(selected_tools) > max_tools:
        st.sidebar.warning(f"The number of selected tools exceeds the maximum allowed length of {max_tools}. Please deselect some tools.")
        return

    # Get the assistant
    llm_os: Assistant
    if "llm_os" not in st.session_state or st.session_state["llm_os"] is None:
        logger.info(f"---*--- Creating {llm_id} LLM OS ---*---")
        llm_os = get_llm_os(
            llm_id=llm_id,
            calculator=calculator_enabled,
            ddg_search=ddg_search_enabled,
            file_tools=file_tools_enabled,
            csv_tools=csv_tools_enabled,
            shell_tools=shell_tools_enabled,
            yfinance_tools=yfinance_tools_enabled,
            data_analyst=data_analyst_enabled,
            python_assistant=python_assistant_enabled,
            research_assistant=research_assistant_enabled,
            investment_assistant=investment_assistant_enabled,
        )
        logger.info(f"Tools in llm_os: {len(llm_os.tools)}")
        st.session_state["llm_os"] = llm_os
        st.sidebar.info(f"Number of tools: {len(llm_os.tools)}")
    else:
        llm_os = st.session_state["llm_os"]
        logger.info(f"Tools in llm_os from session: {len(llm_os.tools)}")
        st.sidebar.info(f"Number of tools: {len(llm_os.tools)}")

    # Create assistant run (i.e. log to database) and save run_id in session state
    try:
        st.session_state["llm_os_run_id"] = llm_os.create_run()
    except Exception:
        st.warning("Could not create LLM OS run, is the database running?")
        return

    # Load existing messages
    assistant_chat_history = llm_os.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history.")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found.")
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
            for delta in llm_os.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    # Save chat history
    if st.sidebar.button("Save Chat History"):
        if "messages" in st.session_state:
            chat_history = st.session_state["messages"]
            chat_history_path = scratch_dir.joinpath("chat_history.json")
            with open(chat_history_path, "w") as f:
                json.dump(chat_history, f, indent=4)
            st.sidebar.success(f"Chat history saved to {chat_history_path}")
    if llm_os.knowledge_base:
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
                        llm_os.knowledge_base.load_documents(web_documents, upsert=True)
                    else:
                        st.sidebar.error("Could not read website")
                    st.session_state[f"{input_url}_uploaded"] = True
                alert.empty()

        # Add CSVs to knowledge base
        if "csv_uploader_key" not in st.session_state:
            st.session_state["csv_uploader_key"] = 200

        uploaded_csv = st.sidebar.file_uploader(
            "Add a CSV :page_facing_up:", type="csv", key=st.session_state["csv_uploader_key"]
        )
        if uploaded_csv is not None:
            alert = st.sidebar.info("Processing CSV...", icon="🧠")
            csv_name = uploaded_csv.name.split(".")[0]
            if f"{csv_name}_uploaded" not in st.session_state:
                csv_path = scratch_dir.joinpath(uploaded_csv.name)
                with open(csv_path, "wb") as f:
                    f.write(uploaded_csv.getbuffer())
                st.session_state[f"{csv_name}_uploaded"] = True
                for tool in llm_os.tools:
                    if isinstance(tool, CsvTools):
                        tool.csvs.append(csv_path)
                        tool.csvs = list(set(tool.csvs))  # Ensure no duplicates
                        st.sidebar.success(f"CSV file '{uploaded_csv.name}' added successfully.")
                        break
            alert.empty()

        # Add PDFs to knowledge base
        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 100

        uploaded_file = st.sidebar.file_uploader(
            "Add a PDF :page_facing_up:", type="pdf", key=st.session_state["file_uploader_key"]
        )
        if uploaded_file is not None:
            alert = st.sidebar.info("Processing PDF...", icon="🧠")
            auto_rag_name = uploaded_file.name.split(".")[0]
            if f"{auto_rag_name}_uploaded" not in st.session_state:
                reader = PDFReader()
                auto_rag_documents: List[Document] = reader.read(uploaded_file)
                if auto_rag_documents:
                    llm_os.knowledge_base.load_documents(auto_rag_documents, upsert=True)
                else:
                    st.sidebar.error("Could not read PDF")
                st.session_state[f"{auto_rag_name}_uploaded"] = True
            alert.empty()

    if llm_os.knowledge_base and llm_os.knowledge_base.vector_db:
        if st.sidebar.button("Clear Knowledge Base"):
            llm_os.knowledge_base.vector_db.clear()
            st.sidebar.success("Knowledge base cleared")

    # Show team member memory
    if llm_os.team and len(llm_os.team) > 0:
        for team_member in llm_os.team:
            if len(team_member.memory.chat_history) > 0:
                with st.status(f"{team_member.name} Memory", expanded=False, state="complete"):
                    with st.container():
                        _team_member_memory_container = st.empty()
                        _team_member_memory_container.json(team_member.memory.get_llm_messages())

    if llm_os.storage:
        llm_os_run_ids: List[str] = llm_os.storage.get_all_run_ids()
        new_llm_os_run_id = st.sidebar.selectbox("Run ID", options=llm_os_run_ids)
        if st.session_state["llm_os_run_id"] != new_llm_os_run_id:
            logger.info(f"---*--- Loading {llm_id} run: {new_llm_os_run_id} ---*---")
            st.session_state["llm_os"] = get_llm_os(
                llm_id=llm_id,
                calculator=calculator_enabled,
                ddg_search=ddg_search_enabled,
                file_tools=file_tools_enabled,
                shell_tools=shell_tools_enabled,
                data_analyst=data_analyst_enabled,
                python_assistant=python_assistant_enabled,
                research_assistant=research_assistant_enabled,
                investment_assistant=investment_assistant_enabled,
                run_id=new_llm_os_run_id,
            )
            st.rerun()
            st.session_state["llm_os"] = get_llm_os(
                llm_id=llm_id,
                calculator=calculator_enabled,
                ddg_search=ddg_search_enabled,
                file_tools=file_tools_enabled,
                shell_tools=shell_tools_enabled,
                data_analyst=data_analyst_enabled,
                python_assistant=python_assistant_enabled,
                research_assistant=research_assistant_enabled,
                investment_assistant=investment_assistant_enabled,
                run_id=new_llm_os_run_id,
            )
            st.rerun()

    if st.sidebar.button("New Run"):
        restart_assistant()


def restart_assistant():
    logger.info("---*--- Restarting Assistant ---*---")
    st.session_state["llm_os"] = None
    st.session_state["llm_os_run_id"] = None
    if "url_scrape_key" in st.session_state:
        st.session_state["url_scrape_key"] += 1
    if "file_uploader_key" in st.session_state:
        st.session_state["file_uploader_key"] += 1
    st.rerun()


main()
