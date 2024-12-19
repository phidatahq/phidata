# IMPORTANT: Before running this script, ensure that the (ANY MODEL )API_KEY environment variable is set.
# To set the API key, follow the instructions below:
# 
# On Windows:
# Open Command Prompt as Administrator and run:
# setx DEEPSEEK_API_KEY "your-api-key-here"
#
# On Unix/Linux:
# Open a terminal and run:
# export DEEPSEEK_API_KEY="your-api-key-here"
#
# NOTE: After setting the API key, restart your terminal or environment to apply the changes  by shuting down the terminal and run the script again. 
from phi.agent import Agent

agent = Agent(markdown=True, monitoring=True)
agent.print_response("Share a 2 sentence horror story")
