from typing import List

import pandas as pd
import streamlit as st
from agno.agent import Agent
from agno.document import Document
from agno.document.reader.csv_reader import CSVReader
from agno.utils.log import logger
from data_visualization import get_viz_agent

st.set_page_config(
    page_title="Data Visualization Agent",
    page_icon="📊",
)

st.title("📊 Data Visualization Agent")
st.markdown("##### 🎨 built using Agno")
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
with st.expander("📝 Example Questions"):
    st.markdown("- What patterns do you see in the data?")
    st.markdown("- Can you analyze the relationship between these columns?")
    st.markdown("- What insights can you provide about this dataset?")


def add_message(role: str, content: str) -> None:
    """Safely add a message to the session state"""
    if not isinstance(st.session_state["messages"], list):
        st.session_state["messages"] = []
    st.session_state["messages"].append({"role": role, "content": content})


def create_visualization(
    df: pd.DataFrame, viz_type: str, x_col: str, y_col: str = None, title: str = None
):
    """Create a visualization using Streamlit's native chart elements"""
    if viz_type == "bar":
        if y_col:
            chart_data = df[[x_col, y_col]].set_index(x_col)
            st.bar_chart(chart_data)
        else:
            chart_data = df[x_col].value_counts().to_frame()
            st.bar_chart(chart_data)
    elif viz_type == "line":
        chart_data = df[[x_col, y_col]].set_index(x_col)
        st.line_chart(chart_data)
    elif viz_type == "scatter":
        chart_data = df[[x_col, y_col]]
        st.scatter_chart(
            data=chart_data,
            x=x_col,
            y=y_col,
        )
    elif viz_type == "area":
        chart_data = df[[x_col, y_col]].set_index(x_col)
        st.area_chart(chart_data)
    elif viz_type == "map":
        # Assuming columns contain latitude and longitude
        st.map(df)

    if title:
        st.caption(title)


def display_tool_calls(tool_calls_container, tools):
    """Display tool calls in a streamlit container with expandable sections."""
    with tool_calls_container.container():
        for tool_call in tools:
            _tool_name = tool_call.get("tool_name")
            _tool_args = tool_call.get("tool_args")
            _content = tool_call.get("content")
            _metrics = tool_call.get("metrics")

            with st.expander(f"🛠️ {_tool_name.replace('_', ' ').title()}", expanded=False):
                if _tool_args:
                    st.markdown("**Arguments:**")
                    st.json(_tool_args)

                if _content:
                    st.markdown("**Results:**")
                    try:
                        st.json(_content)
                    except Exception:
                        st.markdown(_content)

                if _metrics:
                    st.markdown("**Metrics:**")
                    st.json(_metrics)

def export_chat_history():
    """Export chat history as markdown"""
    if "messages" in st.session_state:
        chat_text = "# Data Analysis Agent - Chat History\n\n"
        for msg in st.session_state["messages"]:
            role = "🤖 Assistant" if msg["role"] == "agent" else "👤 User"
            chat_text += f"### {role}\n{msg['content']}\n\n"
        return chat_text
    return ""

def main() -> None:
    # Initialize agent without knowledge base if not exists
    viz_agent: Agent
    if "viz_agent" not in st.session_state:
        logger.info("---*--- Creating new Data Analysis agent ---*---")
        viz_agent = get_viz_agent()
        st.session_state["viz_agent"] = viz_agent
    else:
        viz_agent = st.session_state["viz_agent"]

    # Add utility buttons in sidebar
    st.sidebar.markdown("#### 🛠️ Utilities")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 New Chat"):
            restart_agent()
    with col2:
        if st.download_button(
            "💾 Export Chat",
            export_chat_history(),
            file_name="data_analysis_chat_history.md",
            mime="text/markdown",
        ):
            st.success("Chat history exported!")

    if "messages" not in st.session_state or not isinstance(
        st.session_state["messages"], list
    ):
        st.session_state["messages"] = [
            {
                "role": "agent",
                "content": "Upload a CSV file and I'll help you analyze the data!",
            }
        ]

    # File upload section
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        try:
            # Read the CSV directly into a pandas DataFrame
            df = pd.read_csv(uploaded_file)
            st.session_state["current_df"] = df

            # Display basic info about the dataset
            st.sidebar.write("Dataset Info:")
            st.sidebar.write(f"Rows: {len(df)}")
            st.sidebar.write(f"Columns: {', '.join(df.columns)}")

            # Simple visualization options
            st.sidebar.markdown("### Quick Visualizations")
            viz_type = st.sidebar.selectbox(
                "Chart Type", ["bar", "line", "scatter", "area", "map"]
            )

            x_col = st.sidebar.selectbox("X-axis", df.columns)
            y_col = st.sidebar.selectbox("Y-axis", [None] + list(df.columns))

            if st.sidebar.button("Create Visualization"):
                create_visualization(df, viz_type, x_col, y_col)

            # Process for RAG
            alert = st.sidebar.info("Processing CSV...", icon="🧠")
            auto_rag_name = uploaded_file.name.split(".")[0]
            if f"{auto_rag_name}_uploaded" not in st.session_state:
                reader = CSVReader()
                auto_rag_documents: List[Document] = reader.read(uploaded_file)
                if auto_rag_documents:
                    if viz_agent.knowledge is None:
                        viz_agent = get_viz_agent()
                        st.session_state["viz_agent"] = viz_agent
                    viz_agent.knowledge.load_documents(auto_rag_documents, upsert=True)
                st.session_state[f"{auto_rag_name}_uploaded"] = True
            alert.empty()

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

    # Main chat interface
    chat_container = st.container()
    with chat_container:
        st.empty()

        # Display chat history
        for message in st.session_state["messages"]:
            if message["role"] == "system":
                continue
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Generate response for new user messages
        last_message = (
            st.session_state["messages"][-1] if st.session_state["messages"] else None
        )
        if last_message and last_message.get("role") == "user":
            with st.chat_message("agent"):
                resp_container = st.empty()
                with st.spinner("Analyzing..."):
                    response = ""
                    try:
                        # Create container for tool calls
                        tool_calls_container = st.empty()
                        
                        for delta in viz_agent.run(last_message["content"], stream=True):
                            # Display tool calls if available
                            if hasattr(delta, 'tools') and delta.tools:
                                display_tool_calls(tool_calls_container, delta.tools)
                            
                            if hasattr(delta, 'content') and delta.content is not None:
                                response += delta.content
                                resp_container.markdown(response)
                                
                        st.session_state["messages"].append(
                            {"role": "agent", "content": response}
                        )
                    except Exception as e:
                        error_message = f"Sorry, I encountered an error: {str(e)}"
                        st.error(error_message)
                        st.session_state["messages"].append(
                            {"role": "agent", "content": error_message}
                        )

    # Chat input - moved outside the chat_container
    if prompt := st.chat_input("Ask me about your data..."):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.rerun()  # Add this to force a rerun when new message is added


def restart_agent():
    logger.debug("---*--- Restarting agent ---*---")
    st.session_state["viz_agent"] = None
    st.session_state["knowledge_loaded"] = None  # Reset knowledge base state
    st.session_state["current_file"] = None  # Reset current file
    st.session_state["current_df"] = None  # Reset current dataframe
    st.rerun()


if __name__ == "__main__":
    main()
