"""Run `pip install yfinance` to install dependencies."""

from ollama import Client as OllamaClient
from phi.agent import Agent, RunResponse  # noqa
from phi.model.ollama import Ollama
from phi.playground import Playground, serve_playground_app
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=Ollama(id="llama3.1:8b", client=OllamaClient()),
    tools=[YFinanceTools(stock_price=True)],
    markdown=True,
)

app = Playground(agents=[agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("agent_set_client:app", reload=True)
