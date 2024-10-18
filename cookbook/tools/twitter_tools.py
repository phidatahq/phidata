from phi.agent import Agent
from phi.tools.twitter import TwitterTools

# Export the following environment variables or provide them as arguments to the TwitterTools constructor
# - TWITTER_CONSUMER_KEY
# - TWITTER_CONSUMER_SECRET
# - TWITTER_ACCESS_TOKEN
# - TWITTER_ACCESS_TOKEN_SECRET
# - TWITTER_BEARER_TOKEN

# Initialize the Twitter toolkit
twitter_tools = TwitterTools()

# Create an agent with the twitter toolkit
agent = Agent(
    instructions=[
        "Use your tools to interact with Twitter as the authorized user @phidatahq",
        "When asked to create a tweet, generate appropriate content based on the request",
        "Do not actually post tweets unless explicitly instructed to do so",
        "Provide informative responses about the user's timeline and tweets",
        "Respect Twitter's usage policies and rate limits",
    ],
    tools=[twitter_tools],
    show_tool_calls=True,
)
agent.print_response("Can you retrieve information about this user https://x.com/phidatahq ", markdown=True)

# # Example usage: Reply To a Tweet
# agent.print_response(
#     "Can you reply to this post as a general message as to how great this project is:https://x.com/phidatahq/status/1836101177500479547",
#     markdown=True,
# )
# # Example usage: Get your details
# agent.print_response("Can you return my twitter profile?", markdown=True)
# # Example usage: Send a direct message
# agent.print_response(
#     "Can a send direct message to the user: https://x.com/phidatahq assking you want learn more about them and a link to their community?",
#     markdown=True,
# )
# # Example usage: Create a new tweet
# agent.print_response("Create & post a tweet about the importance of AI ethics", markdown=True)
# # Example usage: Get home timeline
# agent.print_response("Get my timeline", markdown=True)
