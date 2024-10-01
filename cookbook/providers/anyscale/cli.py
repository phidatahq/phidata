from phi.agent import Agent
from phi.model.anyscale import Anyscale

agent = Agent(model=Anyscale(id="mistralai/Mixtral-8x7B-Instruct-v0.1"))
agent.cli_app(markdown=True)
