from agno.agent import Agent
from agno.tools.x import XTools

# Export the following environment variables or provide them as arguments to the XTools constructor
# - X_CONSUMER_KEY
# - X_CONSUMER_SECRET
# - X_ACCESS_TOKEN
# - X_ACCESS_TOKEN_SECRET
# - X_BEARER_TOKEN

# Initialize the x toolkit
x_tools = XTools()

# Create an agent with the X toolkit
agent = Agent(
    instructions=[
        "Use your tools to interact with X (Twitter) as the authorized user @AgnoAgi",
        "When asked to create a post, generate appropriate content based on the request",
        "Do not actually post content unless explicitly instructed to do so",
        "Provide informative responses about the user's timeline and posts",
        "Respect X's usage policies and rate limits",
    ],
    tools=[x_tools],
    show_tool_calls=True,
)
agent.print_response(
    "Can you retrieve information about this user https://x.com/AgnoAgi ",
    markdown=True,
)

# # Example usage: Reply To a Post
# agent.print_response(
#     "Can you reply to this post as a general message as to how great this project is: https://x.com/AgnoAgi",
#     markdown=True,
# )
# # Example usage: Get your details
# agent.print_response("Can you return my x profile?", markdown=True)
# # Example usage: Send a direct message
# agent.print_response(
#     "Can a send direct message to the user: https://x.com/AgnoAgi asking you want learn more about them and a link to their community?",
#     markdown=True,
# )
# # Example usage: Create a new post
# agent.print_response("Create & post content about the importance of AI ethics", markdown=True)
# # Example usage: Get home timeline
# agent.print_response("Get my timeline", markdown=True)
