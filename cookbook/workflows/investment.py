"""Please install dependencies using:
pip install openai yfinance phidata
"""

from typing import Iterator
from pathlib import Path
from shutil import rmtree

from phi.agent import Agent, RunResponse
from phi.workflow import Workflow
from phi.tools.yfinance import YFinanceTools
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger


reports_dir = Path(__file__).parent.joinpath("reports", "investment")
if reports_dir.is_dir():
    rmtree(path=reports_dir, ignore_errors=True)
reports_dir.mkdir(parents=True, exist_ok=True)
stock_analyst_report = str(reports_dir.joinpath("stock_analyst_report.md"))
research_analyst_report = str(reports_dir.joinpath("research_analyst_report.md"))
investment_report = str(reports_dir.joinpath("investment_report.md"))


class InvestmentAnalyst(Workflow):
    stock_analyst: Agent = Agent(
        tools=[YFinanceTools(company_info=True, analyst_recommendations=True, company_news=True)],
        description="You are a Senior Investment Analyst for Goldman Sachs tasked with producing a research report for a very important client.",
        instructions=[
            "You will be provided with a list of companies to write a report on.",
            "Get the company information, analyst recommendations and news for each company",
            "Generate an in-depth report for each company in markdown format with all the facts and details."
            "Note: This is only for educational purposes.",
        ],
        expected_output="Report in markdown format",
        save_response_to_file=stock_analyst_report,
    )

    research_analyst: Agent = Agent(
        name="Research Analyst",
        description="You are a Senior Investment Analyst for Goldman Sachs tasked with producing a ranked list of companies based on their investment potential.",
        instructions=[
            "You will write a research report based on the information provided by the Stock Analyst.",
            "Think deeply about the value of each stock.",
            "Be discerning, you are a skeptical investor focused on maximising growth.",
            "Then rank the companies in order of investment potential, with as much detail about your decision as possible.",
            "Prepare a markdown report with your findings with as much detail as possible.",
        ],
        expected_output="Report in markdown format",
        save_response_to_file=research_analyst_report,
    )

    investment_lead: Agent = Agent(
        name="Investment Lead",
        description="You are a Senior Investment Lead for Goldman Sachs tasked with investing $100,000 for a very important client.",
        instructions=[
            "You have a stock analyst and a research analyst on your team.",
            "The stock analyst has produced a preliminary report on a list of companies, and then the research analyst has ranked the companies based on their investment potential.",
            "Review the report provided by the research analyst and produce a investment proposal for the client.",
            "Provide the amount you'll exist in each company and a report on why.",
        ],
        save_response_to_file=investment_report,
    )

    def run(self, companies: str) -> Iterator[RunResponse]:
        logger.info(f"Getting investment reports for companies: {companies}")
        initial_report: RunResponse = self.stock_analyst.run(companies)
        if initial_report is None or not initial_report.content:
            yield RunResponse(run_id=self.run_id, content="Sorry, could not get the stock analyst report.")
            return

        logger.info("Ranking companies based on investment potential.")
        ranked_companies: RunResponse = self.research_analyst.run(initial_report.content)
        if ranked_companies is None or not ranked_companies.content:
            yield RunResponse(run_id=self.run_id, content="Sorry, could not get the ranked companies.")
            return

        logger.info("Reviewing the research report and producing an investment proposal.")
        yield from self.investment_lead.run(ranked_companies.content, stream=True)


# Run workflow
report: Iterator[RunResponse] = InvestmentAnalyst(debug_mode=False).run(companies="NVDA, TSLA")
# Print the report
pprint_run_response(report, markdown=True, show_time=True)
