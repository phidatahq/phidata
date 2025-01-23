"""Run `pip install yfinance` to install dependencies."""

from agno.agent import Agent, RunResponse  # noqa
from agno.models.ollama import Ollama
from agno.playground import Playground, serve_playground_app
from agno.tools.yfinance import YFinanceTools
from ollama import Client as OllamaClient

agent = Agent(
    model=Ollama(id="llama3.2", client=OllamaClient()),
    tools=[YFinanceTools(stock_price=True)],
    markdown=True,
)

# Print the response in the terminal
agent.print_response("Share a 2 sentence horror story")
