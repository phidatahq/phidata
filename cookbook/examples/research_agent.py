"""🔍 Web Research Agent - Your AI News Research Assistant!

This example shows a research agent that combines web search and scraping capabilities
with journalistic writing skills to produce well-structured news articles.

Key features demonstrated:
- Using DuckDuckGo for web searches
- Article extraction and analysis
- Professional news article generation

Example prompts to try:
- "Analyze the impact of AI on creative industries"
- "Report on recent developments in renewable energy"
- "Investigate the future of remote work trends"
- "Explore the latest advances in electric vehicles"
- "Research the state of space tourism industry"

Please install dependencies using:
pip install openai duckduckgo-search newspaper4k lxml_html_clean agno
"""

from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools

# Initialize the research agent with journalistic capabilities
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools(), Newspaper4kTools()],
    description=dedent("""\
        You are a seasoned NYT investigative journalist with decades of experience
        in researching and writing compelling news articles. Your expertise lies in:

        - Thorough fact-checking and verification
        - Clear and engaging narrative writing
        - Balanced and objective reporting
        - Making complex topics accessible to general readers
        - Crafting headlines that capture attention while maintaining integrity\
    """),
    instructions=[
        "Begin by searching for 10 recent and reliable sources on the topic",
        "Extract and analyze the content from each accessible URL",
        "Cross-reference information for accuracy and consistency",
        "Structure your article in the NYT style with a compelling headline",
        "Include relevant quotes and statistics with proper attribution",
        "Conclude with implications and future outlook",
    ],
    expected_output=dedent("""\
        # {Compelling Headline}

        ## Summary
        {A concise overview of the main story}

        ## Background
        {Context and importance of the topic}

        ## Key Developments
        {Main findings and analysis}
        {Supporting evidence and expert opinions}

        ## Impact and Implications
        {Current and future effects on society/industry}
        {Expert predictions and analysis}

        ## Looking Ahead
        {Future developments and trends}
        {Potential challenges and opportunities}

        ## Sources
        - [Source 1] - Key finding/quote
        - [Source 2] - Key finding/quote
        - [Source 3] - Key finding/quote

        ---
        Article by AI Research Journalist
        New York Times Style Report
        Date: {current_date}\
    """),
    markdown=True,
    show_tool_calls=True,
    add_datetime_to_instructions=True,
)

# Example usage
if __name__ == "__main__":
    # Generate a news article on a current topic
    agent.print_response(
        "The current state of artificial intelligence regulation", stream=True
    )

# More example prompts to try:
"""
Try these research topics:
1. "Analyze the growth of sustainable fashion industry"
2. "Report on breakthrough medical technologies"
3. "Investigate the impact of social media on mental health"
4. "Explore the rise of vertical farming"
5. "Study the evolution of cryptocurrency adoption"
"""
