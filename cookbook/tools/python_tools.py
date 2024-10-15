from phi.agent import Agent
from phi.tools.python import PythonTools

agent = Agent(tools=[PythonTools()], show_tool_calls=True)
agent.print_response("Write a python script for fibonacci series and display the result till the 10th number")
