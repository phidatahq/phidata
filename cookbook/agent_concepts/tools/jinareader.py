from agno.agent import Agent
from agno.tools.jina_tools import JinaReaderTools

agent = Agent(tools=[JinaReaderTools()], debug_mode=True, show_tool_calls=True)
agent.print_response("Summarize: https://github.com/phidatahq")
