import streamlit as st

from phi.tools.streamlit.components import check_password

st.set_page_config(
    page_title="AI Apps",
    page_icon=":orange_heart:",
)
st.title("AI Apps")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def main() -> None:
    st.markdown("---")
    st.markdown("### Select an App:")
    st.markdown("#### 1. PDF Assistant: Chat with PDFs")
    st.markdown("#### 2. Image Assistant: Chat with images")
    st.markdown("#### 3. Website Assistant: Chat with websites")

    st.sidebar.success("Select App from above")


if check_password():
    main()
