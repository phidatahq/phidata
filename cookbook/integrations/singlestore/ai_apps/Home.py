import nest_asyncio
import streamlit as st

nest_asyncio.apply()

st.set_page_config(
    page_title="SingleStore AI Apps",
    page_icon=":orange_heart:",
)
st.title("SingleStore AI Apps")
st.markdown("##### :orange_heart: Built with [phidata](https://github.com/phidatahq/phidata)")


def main() -> None:
    st.markdown("---")
    st.markdown("### Select an AI App from the sidebar:")
    st.markdown("#### 1. Research Assistant: Generate reports about complex topics")
    st.markdown("#### 2. RAG Assistant: Chat with Websites and PDFs")

    st.sidebar.success("Select App from above")


main()
