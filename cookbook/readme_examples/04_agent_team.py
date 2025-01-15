"""🗞️ NYT AI News Team - Your Professional News Squad!
1. Run: `pip install openai duckduckgo-search newspaper4k lxml_html_clean agno` to install the dependencies
"""

from pathlib import Path
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.tools.file import FileTools

# Set up our file storage
urls_file = Path(__file__).parent.joinpath("tmp", "urls__{session_id}.md")
urls_file.parent.mkdir(parents=True, exist_ok=True)

# Create our Research Assistant
searcher = Agent(
    model=OpenAIChat(id="gpt-4"),
    name="Searcher",
    role="Research Assistant",
    instructions=(
        "You are a meticulous research assistant for the New York Times. 🔍\n\n"
        "For any given topic:\n"
        "1. Generate 3 strategic search terms to cover different angles\n"
        "2. Search and analyze web results thoroughly\n"
        "3. Return 10 most credible and relevant URLs\n"
        "4. Focus on high-quality sources worthy of NYT citation"
    ),
    tools=[DuckDuckGoTools()],
    save_response_to_file=str(urls_file),
    markdown=True
)

# Create our Senior Writer
writer = Agent(
    model=OpenAIChat(id="gpt-4"),
    name="Writer",
    role="Senior Writer",
    instructions=(
        "You are a distinguished senior writer for the New York Times. ✍️\n\n"
        f"Your process:\n"
        "1. Analyze all provided URLs thoroughly using `get_article_text`\n"
        "2. Craft a premium NYT-worthy article that is:\n"
        "   - Well-structured and engaging\n"
        "   - Minimum 15 paragraphs long\n"
        "   - Balanced and fact-based\n"
        "   - Properly attributed\n"
        "3. Maintain the NYT's reputation for excellence"
    ),
    tools=[Newspaper4kTools(), FileTools(base_dir=urls_file.parent)],
    markdown=True
)

# Create our Editor-in-Chief
editor = Agent(
    model=OpenAIChat(id="gpt-4"),
    name="Editor",
    team=[searcher, writer],
    role="Editor-in-Chief",
    instructions=(
        "You are the distinguished Editor-in-Chief at the New York Times. 📰\n\n"
        "Your workflow:\n"
        "1. Direct the Research Assistant to gather credible sources\n"
        "2. Guide the Senior Writer in crafting the article\n"
        "3. Polish and perfect the final piece\n"
        "4. Ensure the article meets NYT's exceptional standards\n"
        "\n"
        "Remember: You're the final quality guardian before publication!"
    ),
    markdown=True
)

# Example topics to try:
# - "Write an article about latest developments in AI."
# - "Cover the impact of climate change on New York City."
# - "Report on innovations in sustainable technology."
editor.print_response("Write an article about latest developments in AI.", stream=True)
