"""
Please install dependencies using:
pip install openai yfinance phidata
"""

from pathlib import Path
from shutil import rmtree
from phi.assistant import Assistant
from phi.workflow import Workflow, Task
from phi.tools.yfinance import YFinanceTools
from phi.tools.file import FileTools


reports_dir = Path(__file__).parent.parent.parent.joinpath("wip", "reports")
if reports_dir.exists():
    rmtree(path=reports_dir, ignore_errors=True)
reports_dir.mkdir(parents=True, exist_ok=True)

stock_analyst = Assistant(
    name="Stock Analyst",
    tools=[
        YFinanceTools(company_info=True, analyst_recommendations=True, company_news=True),
        FileTools(base_dir=reports_dir),
    ],
    description="You are a Senior Investment Analyst for Goldman Sachs tasked with producing a research report for a very important client.",
    instructions=[
        "You will be provided with a list of companies to write a report on.",
        "Get the company information, analyst recommendations and news for each company",
        "Save your report to a file in markdown format with the name {company_name.md}.",
        "Note: This is only for educational purposes.",
    ],
    expected_output="Markdown format file with name {company_name.md}",
)
research_analyst = Assistant(
    name="Research Analyst",
    tools=[FileTools(base_dir=reports_dir)],
    description="You are a Senior Investment Analyst for Goldman Sachs tasked with producing a ranked list of companies based on their investment potential.",
    instructions=[
        "You will write a research report based on the information available in files produced by the Stock Analyst.",
        "Read each file 1 by 1.",
        "Then think deeply about whether a stock is valuable or not. Be discerning, you are a skeptical investor focused on maximising growth.",
        "Then rank the companies in order of investment potential, with as much detail about your decision as possible.",
        "Finally, save your research report to a file called {research_draft.md}.",
    ],
    expected_output="Markdown format file with name {research_draft.md}",
)

investment_lead = Assistant(
    name="Investment Lead",
    tools=[FileTools(base_dir=reports_dir)],
    description="You are a Senior Investment Analyst for Goldman Sachs tasked with producing a research report for a very important client.",
    instructions=[
        "Review the report in file {research_draft.md} and product a final report in a file called {research_report.md}.",
        "Make sure to answer the users question correctly, in a clear and concise manner.",
    ],
)

investment_workflow = Workflow(
    name="Investment Research Workflow",
    tasks=[
        Task(
            description="Collect information about NVDA & TSLA.",
            assistant=stock_analyst,
            show_output=False,
        ),
        Task(
            description="Produce a ranked list based on the information provided by the stock analyst.",
            assistant=research_analyst,
            show_output=False,
        ),
        Task(
            description="Review the research report and produce a final report for the client.",
            assistant=investment_lead,
        ),
    ],
    debug_mode=True,
)

investment_workflow.print_response(markdown=True)
