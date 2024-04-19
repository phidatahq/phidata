"""
Inspired by the fantastic work by Matt Shumer (@mattshumer_): https://twitter.com/mattshumer_/status/1771204395285246215

Please run:
pip install openai anthropic newspaper3k lxml_html_clean phidata
"""

from pathlib import Path
from shutil import rmtree
from phi.assistant.team import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.tools.newspaper_toolkit import NewspaperToolkit
from phi.tools.file import FileTools
from phi.llm.anthropic import Claude


reports_dir = Path(__file__).parent.parent.parent.joinpath("junk", "reports")
if reports_dir.exists():
    rmtree(path=reports_dir, ignore_errors=True)
reports_dir.mkdir(parents=True, exist_ok=True)

stock_analyst = Assistant(
    name="Stock Analyst",
    llm=Claude(model="claude-3-haiku-20240307"),
    role="Get current stock price, analyst recommendations and news for a company.",
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_news=True),
        NewspaperToolkit(),
        FileTools(base_dir=reports_dir),
    ],
    description="You are an stock analyst tasked with producing factual reports on companies.",
    instructions=[
        "The investment lead will provide you with a list of companies to write reports on.",
        "Get the current stock price, analyst recommendations and news for the company",
        "If you find any news urls, read the article and include it in the report.",
        "Save your report to a file in markdown format with the name `company_name.md` in lower case.",
        "Let the investment lead know the file name of the report.",
    ],
    # debug_mode=True,
)
research_analyst = Assistant(
    name="Research Analyst",
    role="Writes research reports on stocks.",
    tools=[FileTools(base_dir=reports_dir)],
    description="You are an investment researcher analyst tasked with producing a ranked list of companies based on their investment potential.",
    instructions=[
        "You will write your research report based on the information available in files produced by the stock analyst.",
        "The investment lead will provide you with the files saved by the stock analyst."
        "If no files are provided, list all files in the entire folder and read the files with names matching company names.",
        "Read each file 1 by 1.",
        "Then think deeply about whether a stock is valuable or not. Be discerning, you are a skeptical investor focused on maximising growth.",
        "Finally, save your research report to a file called `research_report.md`.",
    ],
    # debug_mode=True,
)

investment_lead = Assistant(
    name="Investment Lead",
    team=[stock_analyst, research_analyst],
    tools=[FileTools(base_dir=reports_dir)],
    description="You are an investment lead tasked with producing a research report on companies for investment purposes.",
    instructions=[
        "Given a list of companies, first ask the stock analyst to get the current stock price, analyst recommendations and news for these companies.",
        "Ask the stock analyst to write its results to files in markdown format with the name `company_name.md`.",
        "If the stock analyst has not saved the file or saved it with an incorrect name, ask them to save the file again before proceeding."
        "Then ask the research_analyst to write a report on these companies based on the information provided by the stock analyst.",
        "Make sure to provide the research analyst with the files saved by the stock analyst and ask it to read the files directly."
        "The research analyst should save its report to a file called `research_report.md`.",
        "Finally, review the research report and answer the users question. Make sure to answer their question correctly, in a clear and concise manner.",
        "If the research analyst has not completed the report, ask them to complete it before you can answer the users question.",
        "Produce a nicely formatted response to the user, use markdown to format the response.",
    ],
    # debug_mode=True,
)
investment_lead.print_response(
    "How would you invest $10000 in META, GOOG, NVDA and TSLA? Tell me the exact amount you'd invest in each.",
    markdown=True,
)
