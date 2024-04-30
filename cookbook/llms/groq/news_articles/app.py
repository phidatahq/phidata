import nest_asyncio
from typing import Optional

import streamlit as st
from duckduckgo_search import DDGS
from phi.tools.tavily import TavilyTools
from phi.tools.newspaper4k import Newspaper4k
from phi.utils.log import logger

from assistants import get_article_summarizer, get_article_writer  # type: ignore

nest_asyncio.apply()
st.set_page_config(
    page_title="News Articles",
    page_icon=":orange_heart:",
)
st.title("News Articles powered by Groq")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def truncate_text(text: str, words: int) -> str:
    return " ".join(text.split()[:words])


def main() -> None:
    # Get model
    llm_model = st.sidebar.selectbox(
        "Select Model", options=["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]
    )
    # Set assistant_type in session state
    if "llm_model" not in st.session_state:
        st.session_state["llm_model"] = llm_model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["llm_model"] != llm_model:
        st.session_state["llm_model"] = llm_model
        st.rerun()

    # Get topic for report
    input_topic = st.text_input(
        ":spiral_calendar_pad: Enter a topic for the article",
        value="Superfast Llama 3 inference on Groq Cloud",
    )
    # Button to write article
    write_article = st.button("Write Article")
    if write_article:
        st.session_state["topic"] = input_topic

    # Checkboxes for research options
    st.sidebar.markdown("## Research Options")
    search_news = st.sidebar.checkbox("Research news articles", value=True)
    search_tavily = st.sidebar.checkbox("Research using Tavily", value=False)
    num_search_results = st.sidebar.slider(
        ":sparkles: Number of Search Results",
        min_value=3,
        max_value=20,
        value=7,
        help="Number of results to search for, note only the articles that can be read will be summarized.",
    )
    per_article_summary_length = st.sidebar.slider(
        ":sparkles: Length of Article Summary",
        min_value=100,
        max_value=2000,
        value=500,
        step=100,
        help="Number of words per article summary",
    )
    news_summary_length = st.sidebar.slider(
        ":sparkles: Length of News Summary",
        min_value=1000,
        max_value=10000,
        value=4000,
        step=100,
        help="Number of words in the news summary, this should fit the context length of the model.",
    )
    tavily_summary_length = st.sidebar.slider(
        ":sparkles: Length of Tavily Summary",
        min_value=100,
        max_value=5000,
        value=500,
        step=100,
        help="Number of words in the tavily summary, this should fit the context length of the model.",
    )
    st.sidebar.markdown("---")

    st.sidebar.markdown("## Trending Topics")
    if st.sidebar.button("Superfast Llama 3 inference on Groq Cloud"):
        st.session_state["topic"] = "Llama 3 on Groq Cloud"

    if st.sidebar.button("AI in Healthcare"):
        st.session_state["topic"] = "AI in Healthcare"

    if st.sidebar.button("Language Agent Tree Search"):
        st.session_state["topic"] = "Language Agent Tree Search"

    if "topic" in st.session_state:
        article_topic = st.session_state["topic"]

        news_results = []
        news_summary: Optional[str] = None
        if search_news:
            with st.status("Reading News", expanded=False) as status:
                with st.container():
                    news_container = st.empty()
                    ddgs = DDGS()
                    newspaper_tools = Newspaper4k()
                    results = ddgs.news(keywords=article_topic, max_results=num_search_results)
                    for r in results:
                        if "url" in r:
                            article_data = newspaper_tools.get_article_data(r["url"])
                            if article_data and "text" in article_data:
                                r["text"] = article_data["text"]
                                news_results.append(r)
                                if news_results:
                                    news_container.write(news_results)
                if news_results:
                    news_container.write(news_results)
                status.update(label="News Search Complete", state="complete", expanded=False)

            if len(news_results) > 0:
                news_summary = ""
                with st.status("Summarizing News", expanded=False) as status:
                    article_summarizer = get_article_summarizer(length=per_article_summary_length)
                    with st.container():
                        summary_container = st.empty()
                        for news_result in news_results:
                            news_summary += f"### {news_result['title']}\n\n"
                            news_summary += f"- Date: {news_result['date']}\n\n"
                            news_summary += f"- URL: {news_result['url']}\n\n"
                            news_summary += f"#### Introduction\n\n{news_result['body']}\n\n"

                            _summary: str = article_summarizer.run(news_result["text"], stream=False)
                            _summary_length = len(_summary.split())
                            if _summary_length > news_summary_length:
                                _summary = truncate_text(_summary, news_summary_length)
                                logger.info(
                                    f"Truncated summary for {news_result['title']} to {news_summary_length} words."
                                )
                            news_summary += "#### Summary\n\n"
                            news_summary += _summary
                            news_summary += "\n\n---\n\n"
                            if news_summary:
                                summary_container.markdown(news_summary)
                            if len(news_summary.split()) > news_summary_length:
                                logger.info(f"Stopping news summary at length: {len(news_summary.split())}")
                                break
                    if news_summary:
                        summary_container.markdown(news_summary)
                    status.update(label="News Summarization Complete", state="complete", expanded=False)

        tavily_content: Optional[str] = None
        if search_tavily:
            with st.status("Searching Tavily", expanded=True) as status:
                with st.container():
                    tavily_container = st.empty()
                    tavily_content = TavilyTools().web_search_using_tavily(article_topic)
                    if tavily_content:
                        if len(tavily_content.split()) > tavily_summary_length:
                            tavily_content = truncate_text(tavily_content, tavily_summary_length)
                            logger.info(f"Truncated tavily content to {tavily_summary_length} words.")
                        tavily_container.markdown(tavily_content)
                status.update(label="Tavily Search Complete", state="complete", expanded=False)

        if news_summary is None and tavily_content is None:
            st.write("Sorry could not find any news or web search results. Please try again.")
            return

        article_draft = ""
        article_draft += f"# Topic: {article_topic}\n\n"
        if news_summary:
            article_draft += "## News Summary\n\n"
            article_draft += "This section provides a summary of the news articles about this topic.\n\n"
            article_draft += "<news_summary>\n\n"
            article_draft += f"{news_summary}\n\n"
            article_draft += "</news_summary>\n\n"
        if tavily_content:
            article_draft += "## Additional Web Search Results\n\n"
            article_draft += "This section provides additional web search results about the topic.\n\n"
            article_draft += "<additional_web_search_results>\n\n"
            article_draft += f"{tavily_content}\n\n"
            article_draft += "</additional_web_search_results>\n\n"

        with st.status("Writing Draft", expanded=True) as status:
            with st.container():
                draft_container = st.empty()
                draft_container.markdown(article_draft)
            status.update(label="Draft Complete", state="complete", expanded=False)

        article_writer = get_article_writer()
        with st.spinner("Writing Article..."):
            final_report = ""
            final_report_container = st.empty()
            for delta in article_writer.run(article_draft):
                final_report += delta  # type: ignore
                final_report_container.markdown(final_report)

    st.sidebar.markdown("---")
    if st.sidebar.button("Restart"):
        st.rerun()


main()
