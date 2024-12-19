from phi.agent import Agent, RunResponse
from phi.model.deepseek import DeepSeekChat

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

# Initialize the agent with the DeepSeekChat model
agent = Agent(model=DeepSeekChat(), markdown=True)

# Example 1: Get the response in a variable
# Uncomment the following lines to use:
# run: RunResponse = agent.run("Share a 2 sentence horror story.")
# print(run.content)

# Example 2: Print the response in the terminal
print("Printing the response in the terminal")
agent.print_response(
    "Give me a code for a React app which says 'Hello World' and provide all file code"
)
