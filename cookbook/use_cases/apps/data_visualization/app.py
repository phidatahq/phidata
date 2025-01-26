from typing import List

import pandas as pd
import streamlit as st
from agno.agent import Agent
from agno.document import Document
from agno.document.reader.csv_reader import CSVReader
from agno.utils.log import logger
from data_visualization import get_viz_agent

st.set_page_config(
    page_title="Data Analysis Agent",
    page_icon="📊",
)

st.title("📊 Data Analysis Agent")
st.markdown("##### 🎨 built using Agno")

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


def main() -> None:
    # Initialize agent without knowledge base if not exists
    viz_agent: Agent
    if "viz_agent" not in st.session_state:
        logger.info("---*--- Creating new Data Analysis agent ---*---")
        viz_agent = get_viz_agent()  # Initialize without knowledge base
        st.session_state["viz_agent"] = viz_agent
    else:
        viz_agent = st.session_state["viz_agent"]

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

    # Chat interface
    if prompt := st.chat_input("Ask me about your data..."):
        add_message("user", prompt)

    # Display chat messages
    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Generate response for new user messages
    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        with st.chat_message("agent"):
            with st.spinner("Analyzing..."):
                response = ""
                resp_container = st.empty()
                try:
                    for delta in viz_agent.run(last_message["content"], stream=True):
                        if hasattr(delta, "content") and delta.content is not None:
                            response += delta.content
                            try:
                                resp_container.markdown(response)
                            except Exception as e:
                                st.error(f"Error updating response: {str(e)}")
                                break
                    st.session_state["messages"].append(
                        {"role": "agent", "content": response}
                    )
                except Exception as e:
                    st.error(f"Error processing request: {str(e)}")
                    st.session_state["messages"].append(
                        {
                            "role": "agent",
                            "content": "Sorry, I encountered an error while processing your request.",
                        }
                    )

    st.sidebar.markdown("---")
    if st.sidebar.button("New Session"):
        restart_agent()


def restart_agent():
    logger.debug("---*--- Restarting agent ---*---")
    st.session_state["viz_agent"] = None
    st.session_state["knowledge_loaded"] = None  # Reset knowledge base state
    st.session_state["current_file"] = None  # Reset current file
    st.session_state["current_df"] = None  # Reset current dataframe
    st.rerun()


if __name__ == "__main__":
    main()
