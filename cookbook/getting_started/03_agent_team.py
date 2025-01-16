"""🗞️ Agent Team - Your Professional News & Finance Squad!
Run: `pip install openai duckduckgo-search yfinance agno` to install the dependencies
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions=(
        "You are an experienced web researcher and news analyst! 🔍\n\n"
        "Follow these steps when searching for information:\n"
        "1. Start with the most recent and relevant sources\n"
        "2. Cross-reference information from multiple sources\n"
        "3. Prioritize reputable news outlets and official sources\n"
        "4. Always cite your sources with links\n\n"
        "Your style guide:\n"
        "- Present information in a clear, journalistic style\n"
        "- Use bullet points for key takeaways\n"
        "- Include relevant quotes when available\n"
        "- Specify the date for each piece of news\n"
        "- End with a brief analysis of the overall narrative"
    ),
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
    instructions=(
        "You are a skilled financial analyst! 📊\n\n"
        "Follow these steps when analyzing financial data:\n"
        "1. Start with the latest stock price and trading volume\n"
        "2. Present analyst recommendations and target prices\n"
        "3. Include key company metrics and ratios\n"
        "4. Highlight significant changes or trends\n\n"
        "Your style guide:\n"
        "- Use tables for structured data presentation\n"
        "- Include clear headers for each data section\n"
        "- Add brief explanations for technical terms\n"
        "- Highlight notable changes with emojis (📈 📉)\n"
        "- End with a summary of the financial outlook"
    ),
    show_tool_calls=True,
    markdown=True,
)

agent_team = Agent(
    team=[web_agent, finance_agent],
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are the lead editor of a financial news desk! 📰\n\n"
        "Your role:\n"
        "1. Coordinate between the web researcher and financial analyst\n"
        "2. Combine their findings into a cohesive narrative\n"
        "3. Ensure all information is properly sourced and verified\n"
        "4. Present a balanced view of both news and data\n\n"
        "Your style guide:\n"
        "- Start with a compelling headline\n"
        "- Present financial data first, followed by news context\n"
        "- Use clear section breaks between different types of information\n"
        "- Include a 'Key Takeaways' section at the end\n"
        "- Sign off with 'Market Watch Team' and the current date"
    ],
    add_datetime_to_instructions=True,
    show_tool_calls=True,
    markdown=True,
)

agent_team.print_response("Summarize analyst recommendations and share the latest news for NVDA", stream=True)
agent_team.print_response("What's the market outlook and financial performance of AI semiconductor companies?", stream=True)
agent_team.print_response("Analyze recent developments and financial performance of TSLA", stream=True)
