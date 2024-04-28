import nest_asyncio
import yfinance as yf
import streamlit as st
from duckduckgo_search import DDGS
from phi.assistant import Assistant
from phi.utils.log import logger

from assistants import get_invstment_research_assistant  # type: ignore

nest_asyncio.apply()
st.set_page_config(
    page_title="Investment Researcher",
    page_icon=":orange_heart:",
)
st.title("Investment Researcher")
st.markdown("##### :orange_heart: Built using [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["research_assistant"] = None
    st.rerun()


def main() -> None:
    # Get LLM Model
    model = (
        st.sidebar.selectbox("Select LLM", options=["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"])
        or "llama3-70b-8192"
    )
    # Set llm in session state
    if "model" not in st.session_state:
        st.session_state["model"] = model
    # Restart the assistant if model changes
    elif st.session_state["model"] != model:
        st.session_state["model"] = model
        restart_assistant()

    # Get the assistant
    research_assistant: Assistant
    if "research_assistant" not in st.session_state or st.session_state["research_assistant"] is None:
        research_assistant = get_invstment_research_assistant(model=model)
        st.session_state["research_assistant"] = research_assistant
    else:
        research_assistant = st.session_state["research_assistant"]

    # Get ticker for report
    ticker_to_research = st.sidebar.text_input(
        ":female-scientist: Enter a ticker to research",
        value="NVDA",
    )

    # Checkboxes for research options
    st.sidebar.markdown("## Research Options")
    get_company_info = st.sidebar.checkbox("Company Info", value=True)
    get_company_news = st.sidebar.checkbox("Company News", value=True)
    get_analyst_recommendations = st.sidebar.checkbox("Analyst Recommendations", value=True)
    get_upgrades_downgrades = st.sidebar.checkbox("Upgrades/Downgrades", value=True)

    # Ticker object
    ticker = yf.Ticker(ticker_to_research)

    # -*- Generate Research Report
    generate_report = st.sidebar.button("Generate Report")
    if generate_report:
        report_input = ""

        if get_company_info:
            with st.status("Getting Company Info", expanded=True) as status:
                with st.container():
                    company_info_container = st.empty()
                    company_info_full = ticker.info
                    if company_info_full:
                        company_info_container.json(company_info_full)
                        company_info_cleaned = {
                            "Name": company_info_full.get("shortName"),
                            "Symbol": company_info_full.get("symbol"),
                            "Current Stock Price": f"{company_info_full.get('regularMarketPrice', company_info_full.get('currentPrice'))} {company_info_full.get('currency', 'USD')}",
                            "Market Cap": f"{company_info_full.get('marketCap', company_info_full.get('enterpriseValue'))} {company_info_full.get('currency', 'USD')}",
                            "Sector": company_info_full.get("sector"),
                            "Industry": company_info_full.get("industry"),
                            "Address": company_info_full.get("address1"),
                            "City": company_info_full.get("city"),
                            "State": company_info_full.get("state"),
                            "Zip": company_info_full.get("zip"),
                            "Country": company_info_full.get("country"),
                            "EPS": company_info_full.get("trailingEps"),
                            "P/E Ratio": company_info_full.get("trailingPE"),
                            "52 Week Low": company_info_full.get("fiftyTwoWeekLow"),
                            "52 Week High": company_info_full.get("fiftyTwoWeekHigh"),
                            "50 Day Average": company_info_full.get("fiftyDayAverage"),
                            "200 Day Average": company_info_full.get("twoHundredDayAverage"),
                            "Website": company_info_full.get("website"),
                            "Summary": company_info_full.get("longBusinessSummary"),
                            "Analyst Recommendation": company_info_full.get("recommendationKey"),
                            "Number Of Analyst Opinions": company_info_full.get("numberOfAnalystOpinions"),
                            "Employees": company_info_full.get("fullTimeEmployees"),
                            "Total Cash": company_info_full.get("totalCash"),
                            "Free Cash flow": company_info_full.get("freeCashflow"),
                            "Operating Cash flow": company_info_full.get("operatingCashflow"),
                            "EBITDA": company_info_full.get("ebitda"),
                            "Revenue Growth": company_info_full.get("revenueGrowth"),
                            "Gross Margins": company_info_full.get("grossMargins"),
                            "Ebitda Margins": company_info_full.get("ebitdaMargins"),
                        }
                        company_info_md = "## Company Info\n\n"
                        for key, value in company_info_cleaned.items():
                            if value:
                                company_info_md += f"  - {key}: {value}\n\n"
                        # company_info_container.markdown(company_info_md)
                        report_input += "This section contains information about the company.\n\n"
                        report_input += company_info_md
                        report_input += "---\n"
                status.update(label="Company Info available", state="complete", expanded=False)

        if get_company_news:
            with st.status("Getting Company News", expanded=True) as status:
                with st.container():
                    company_news_container = st.empty()
                    ddgs = DDGS()
                    company_news = ddgs.news(keywords=ticker_to_research, max_results=5)
                    company_news_container.json(company_news)
                    if len(company_news) > 0:
                        company_news_md = "## Company News\n\n\n"
                        for news_item in company_news:
                            company_news_md += f"#### {news_item['title']}\n\n"
                            if "date" in news_item:
                                company_news_md += f"  - Date: {news_item['date']}\n\n"
                            if "url" in news_item:
                                company_news_md += f"  - Link: {news_item['url']}\n\n"
                            if "source" in news_item:
                                company_news_md += f"  - Source: {news_item['source']}\n\n"
                            if "body" in news_item:
                                company_news_md += f"{news_item['body']}"
                            company_news_md += "\n\n"
                        company_news_container.markdown(company_news_md)
                        report_input += "This section contains the most recent news articles about the company.\n\n"
                        report_input += company_news_md
                        report_input += "---\n"
                status.update(label="Company News available", state="complete", expanded=False)

        if get_analyst_recommendations:
            with st.status("Getting Analyst Recommendations", expanded=True) as status:
                with st.container():
                    analyst_recommendations_container = st.empty()
                    analyst_recommendations = ticker.recommendations
                    if not analyst_recommendations.empty:
                        analyst_recommendations_container.write(analyst_recommendations)
                        analyst_recommendations_md = analyst_recommendations.to_markdown()
                        report_input += "## Analyst Recommendations\n\n"
                        report_input += "This table outlines the most recent analyst recommendations for the stock.\n\n"
                        report_input += f"{analyst_recommendations_md}\n"
                    report_input += "---\n"
                status.update(label="Analyst Recommendations available", state="complete", expanded=False)

        if get_upgrades_downgrades:
            with st.status("Getting Upgrades/Downgrades", expanded=True) as status:
                with st.container():
                    upgrades_downgrades_container = st.empty()
                    upgrades_downgrades = ticker.upgrades_downgrades[0:20]
                    if not upgrades_downgrades.empty:
                        upgrades_downgrades_container.write(upgrades_downgrades)
                        upgrades_downgrades_md = upgrades_downgrades.to_markdown()
                        report_input += "## Upgrades/Downgrades\n\n"
                        report_input += "This table outlines the most recent upgrades and downgrades for the stock.\n\n"
                        report_input += f"{upgrades_downgrades_md}\n"
                    report_input += "---\n"
                status.update(label="Upgrades/Downgrades available", state="complete", expanded=False)

        with st.status("Generating Draft", expanded=True) as status:
            with st.container():
                draft_report_container = st.empty()
                draft_report_container.markdown(report_input)
            status.update(label="Draft Generated", state="complete", expanded=False)

        with st.spinner("Generating Report"):
            final_report = ""
            final_report_container = st.empty()
            report_message = f"Please generate a report about: {ticker_to_research}\n\n\n"
            report_message += report_input
            for delta in research_assistant.run(report_message):
                final_report += delta  # type: ignore
                final_report_container.markdown(final_report)

    st.sidebar.markdown("---")
    if st.sidebar.button("New Run"):
        restart_assistant()


main()
