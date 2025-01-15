"""Run `pip install yfinance` to install dependencies."""

from ollama import Client as OllamaClient
from agno.agent import Agent, RunResponse  # noqa
from agno.models.ollama import Ollama
from agno.playground import Playground, serve_playground_app
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=Ollama(id="llama3.2", client=OllamaClient()),
    tools=[YFinanceTools(stock_price=True)],
    markdown=True,
)

app = Playground(agents=[agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("agent_set_client:app", reload=True)
