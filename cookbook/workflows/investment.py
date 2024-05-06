"""
Please install dependencies using:
pip install openai newspaper4k lxml_html_clean yfinance phidata
"""

from textwrap import dedent
from pathlib import Path
from shutil import rmtree
from phi.assistant import Assistant
from phi.workflow import Workflow, Task
from phi.tools.yfinance import YFinanceTools
from phi.tools.newspaper4k import Newspaper4k
from phi.tools.file import FileTools


reports_dir = Path(__file__).parent.parent.parent.joinpath("wip", "reports")
if reports_dir.exists():
    rmtree(path=reports_dir, ignore_errors=True)
reports_dir.mkdir(parents=True, exist_ok=True)

stock_analyst = Assistant(
    name="Stock Analyst",
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True),
        Newspaper4k(),
        FileTools(base_dir=reports_dir),
    ],
    description="You are a stock analyst tasked with producing factual reports on companies.",
    instructions=[
        "You will be provided with a list of companies to write reports on.",
        "Get the current stock price and analyst recommendations for the company",
        "Save your report to a file in markdown format with the name `company_name.md` in lower case.",
    ],
    add_to_system_prompt="This is only for educational purposes.",
    # debug_mode=True,
)
research_analyst = Assistant(
    name="Research Analyst",
    tools=[FileTools(base_dir=reports_dir)],
    description="You are an investment researcher analyst tasked with producing a ranked list of companies based on their investment potential.",
    instructions=[
        "You will write your research report based on the information available in files produced by the stock analyst.",
        "Read each file 1 by 1.",
        "Then think deeply about whether a stock is valuable or not. Be discerning, you are a skeptical investor focused on maximising growth.",
        "Finally, save your research report to a file called `research_report.md`.",
    ],
    # debug_mode=True,
)

investment_lead = Assistant(
    name="Investment Lead",
    tools=[FileTools(base_dir=reports_dir)],
    description="You are an investment lead tasked with producing a research report on companies for investment purposes.",
    # debug_mode=True,
)

investment_workflow = Workflow(
    name="Investment Research Workflow",
    tasks=[
        Task(
            description=dedent("""\
            Collect information about companies and write the results to files in markdown format with the name `company_name.md`.
            """),
            assistant=stock_analyst,
            show_output=False,
        ),
        Task(
            description=dedent("""\
            Write a report based on the information provided by the stock analyst.
            Read the files saved by the stock analyst and write a report to a file called `research_report.md`.
            """),
            assistant=research_analyst,
            show_output=False,
        ),
        Task(
            description=dedent("""\
            Review the research report and answer the users question.
            Make sure to answer their question correctly, in a clear and concise manner.
            Produce a nicely formatted response to the user, use markdown to format the response.
            """),
            assistant=investment_lead,
            # show_output=True
        ),
    ],
    debug_mode=True,
)

investment_workflow.print_response(
    "NVDA",
    markdown=True,
)
