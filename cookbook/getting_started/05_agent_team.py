"""🗞️ Agent Team - Your Professional News & Finance Squad!

This example shows how to create a powerful team of AI agents working together
to provide comprehensive financial analysis and news reporting. The team consists of:
1. Web Agent: Searches and analyzes latest news
2. Finance Agent: Analyzes financial data and market trends
3. Lead Editor: Coordinates and combines insights from both agents

Example prompts to try:
- "What's the latest news and financial performance of Apple (AAPL)?"
- "Analyze the impact of AI developments on NVIDIA's stock (NVDA)"
- "How are EV manufacturers performing? Focus on Tesla (TSLA) and Rivian (RIVN)"
- "What's the market outlook for semiconductor companies like AMD and Intel?"
- "Summarize recent developments and stock performance of Microsoft (MSFT)"

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
        "5. Focus on market-moving news and significant developments\n\n"
        "Your style guide:\n"
        "- Present information in a clear, journalistic style\n"
        "- Use bullet points for key takeaways\n"
        "- Include relevant quotes when available\n"
        "- Specify the date and time for each piece of news\n"
        "- Highlight market sentiment and industry trends\n"
        "- End with a brief analysis of the overall narrative\n"
        "- Pay special attention to regulatory news, earnings reports, and strategic announcements"
    ),
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)
    ],
    instructions=(
        "You are a skilled financial analyst with expertise in market data! 📊\n\n"
        "Follow these steps when analyzing financial data:\n"
        "1. Start with the latest stock price, trading volume, and daily range\n"
        "2. Present detailed analyst recommendations and consensus target prices\n"
        "3. Include key metrics: P/E ratio, market cap, 52-week range\n"
        "4. Analyze trading patterns and volume trends\n"
        "5. Compare performance against relevant sector indices\n\n"
        "Your style guide:\n"
        "- Use tables for structured data presentation\n"
        "- Include clear headers for each data section\n"
        "- Add brief explanations for technical terms\n"
        "- Highlight notable changes with emojis (📈 📉)\n"
        "- Use bullet points for quick insights\n"
        "- Compare current values with historical averages\n"
        "- End with a data-driven financial outlook"
    ),
    show_tool_calls=True,
    markdown=True,
)

agent_team = Agent(
    team=[web_agent, finance_agent],
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are the lead editor of a prestigious financial news desk! 📰\n\n"
        "Your role:\n"
        "1. Coordinate between the web researcher and financial analyst\n"
        "2. Combine their findings into a compelling narrative\n"
        "3. Ensure all information is properly sourced and verified\n"
        "4. Present a balanced view of both news and data\n"
        "5. Highlight key risks and opportunities\n\n"
        "Your style guide:\n"
        "- Start with an attention-grabbing headline\n"
        "- Begin with a powerful executive summary\n"
        "- Present financial data first, followed by news context\n"
        "- Use clear section breaks between different types of information\n"
        "- Include relevant charts or tables when available\n"
        "- Add 'Market Sentiment' section with current mood\n"
        "- Include a 'Key Takeaways' section at the end\n"
        "- End with 'Risk Factors' when appropriate\n"
        "- Sign off with 'Market Watch Team' and the current date"
    ],
    add_datetime_to_instructions=True,
    show_tool_calls=True,
    markdown=True,
)

# Example usage with diverse queries
agent_team.print_response(
    "Summarize analyst recommendations and share the latest news for NVDA", stream=True
)
agent_team.print_response(
    "What's the market outlook and financial performance of AI semiconductor companies?",
    stream=True,
)
agent_team.print_response(
    "Analyze recent developments and financial performance of TSLA", stream=True
)

# More example prompts to try:
"""
Advanced queries to explore:
1. "Compare the financial performance and recent news of major cloud providers (AMZN, MSFT, GOOGL)"
2. "What's the impact of recent Fed decisions on banking stocks? Focus on JPM and BAC"
3. "Analyze the gaming industry outlook through ATVI, EA, and TTWO performance"
4. "How are social media companies performing? Compare META and SNAP"
5. "What's the latest on AI chip manufacturers and their market position?"
"""