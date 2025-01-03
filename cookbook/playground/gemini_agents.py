from phi.agent import Agent
from phi.tools.yfinance import YFinanceTools
from phi.playground import Playground, serve_playground_app
from phi.model.google import Gemini

finance_agent = Agent(
    name="Finance Agent",
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[YFinanceTools(stock_price=True)],
    debug_mode=True,
)

app = Playground(agents=[finance_agent]).get_app(use_async=False)

if __name__ == "__main__":
    serve_playground_app("gemini_agents:app", reload=True)
