import streamlit as st
from typing import Dict, Any
from phi.agent import Agent
from phi.tools.postgres import PostgresTools
from phi.tools.druiddb import DruidTools
from phi.model.openai import OpenAIChat


def get_session_state():
    """Initialize or get the session state"""
    if not hasattr(st.session_state, "initialized"):
        st.session_state.initialized = True
        st.session_state.agent = None
        st.session_state.messages = []
        st.session_state.db_type = None
        st.session_state.connection_status = None

    return st.session_state


def create_postgres_agent(conn_details: Dict[str, Any]) -> Agent:
    """Create a PostgreSQL agent with the given connection details"""
    postgres_tools = PostgresTools(
        db_name=conn_details["database"],
        user=conn_details["user"],
        password=conn_details["password"],
        host=conn_details["host"],
        port=conn_details["port"],
    )

    return Agent(
        name="postgres_analyst",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[postgres_tools],
        description="I am an expert PostgreSQL analyst that helps you analyze data in PostgreSQL databases. I execute queries and provide accurate results without making assumptions.",
        instructions=[
            # Core Database Interaction
            "Use show_tables() to list available tables",
            "Use describe_table() to understand table structure",
            "Use get_schema_info() to find correct schemas",  # Added: New tool instruction
            "Use get_table_sample() before complex analysis",  # Added: New tool instruction
            "Use get_column_stats() for data profiling",  # Added: New tool instruction
            # Query Building Guidelines
            "Always validate queries before execution",
            "Use LIMIT clauses for large tables",
            "Include appropriate WHERE clauses",
            "Use explicit schema names in queries",
            # Error Handling
            "Validate table existence before querying",
            "Handle NULL values explicitly",
            "Provide clear error explanations",
            # Performance Guidelines
            "Sample data before full table scans",
            "Use indexes when available",
            "Consider query timeout limits",
            # Response Format
            "Return only requested information",
            "Format numbers appropriately",
            "Include execution timestamps",
            # Data Safety
            "Never execute DROP or DELETE without confirmation",
            "Verify schema/table names before queries",
            "Respect row limit settings",
        ],
        markdown=True,
        show_tool_calls=True,
        debug_mode=True,
    )


def create_druid_agent(conn_details: Dict[str, Any]) -> Agent:
    """Create a Druid agent with the given connection details"""
    druid_tools = DruidTools(
        host=conn_details["host"],
        port=conn_details["port"],
        list_tables=True,
        describe_table=True,
        run_query=True,
        table_sample=True,
        table_stats=True,
    )

    return Agent(
        name="druid_analyst",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[druid_tools],
        description="I am an expert Druid analyst that helps you analyze data in Druid databases. I execute queries and provide accurate results without making assumptions.",
        instructions=[
            "NEVER make up or hallucinate data - if a query fails, explain the error clearly",
            "NEVER show example/fake data - only show actual query results",
            "ONLY use database tools when explicitly asked for database information",
            "For greetings or general questions, respond naturally WITHOUT using any tools",
            "Use list_tables when: User asks to see/list/show tables",
            "Use table_sample when: User asks for data samples",
            "Use table_stats when: User asks for table statistics",
            "Use run_query when: User wants to analyze data or asks for something specific",
            "When showing results:",
            "1. Show the tool being called",
            "2. Show the actual results or error message",
            "3. Explain what the results mean",
            "4. If there's an error, explain what went wrong",
        ],
        markdown=True,
        show_tool_calls=True,
        debug_mode=True,
    )


@st.cache_data(show_spinner=False)
def test_connection(db_type: str, conn_details: Dict[str, Any]) -> tuple[bool, str]:
    """Test the database connection and return success status and message"""
    try:
        if db_type == "PostgreSQL":
            agent = create_postgres_agent(conn_details)
        else:  # Druid
            agent = create_druid_agent(conn_details)

        # Test the connection by listing tables
        response = agent.run("List tables")
        return True, "Connection successful!"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def render_sidebar():
    """Render the sidebar with database configuration options"""
    with st.sidebar:
        st.header("Database Configuration")
        state = get_session_state()

        # Database type selection
        db_type = st.radio("Select Database Type", ["PostgreSQL", "Druid"])

        with st.form("connection_form", clear_on_submit=False):
            if db_type == "PostgreSQL":
                host = st.text_input("Host", "localhost")
                port = st.number_input("Port", value=5432)
                database = st.text_input("Database Name")
                user = st.text_input("Username")
                password = st.text_input("Password", type="password")
                conn_details = {"host": host, "port": port, "database": database, "user": user, "password": password}
            else:  # Druid
                host = st.text_input("Host", "localhost")
                port = st.number_input("Port", value=8888)
                conn_details = {"host": host, "port": port}

            if st.form_submit_button("Connect", use_container_width=True):
                with st.spinner("Testing connection..."):
                    success, message = test_connection(db_type, conn_details)
                    if success:
                        state.connection_status = "success"
                        state.db_type = db_type
                        if db_type == "PostgreSQL":
                            state.agent = create_postgres_agent(conn_details)
                        else:
                            state.agent = create_druid_agent(conn_details)
                        state.messages = []  # Reset chat history
                        st.success(message)
                    else:
                        state.connection_status = "failed"
                        st.error(message)


def render_chat_interface():
    """Render the main chat interface"""
    state = get_session_state()

    if state.agent:
        # Display chat messages
        for message in state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("Ask me about your data...", key="chat_input"):
            # Add user message to chat history
            state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get agent response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        response = state.agent.run(prompt)
                        response_content = response.content
                        st.markdown(response_content)
                        # Add assistant response to chat history
                        state.messages.append({"role": "assistant", "content": response_content})
                    except Exception as e:
                        error_message = f"Error: {str(e)}"
                        st.error(error_message)
                        state.messages.append({"role": "assistant", "content": error_message})
    else:
        st.info("👈 Please connect to a database using the sidebar to start chatting.")


def main():
    st.set_page_config(
        page_title="Database Chat Assistant", page_icon="🤖", layout="wide", initial_sidebar_state="expanded"
    )

    st.title("🤖 Database Chat Assistant")

    # Initialize session state
    state = get_session_state()

    # Render sidebar and chat interface
    render_sidebar()
    render_chat_interface()


if __name__ == "__main__":
    main()
