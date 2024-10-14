from phi.agent import Agent
from phi.tools.twitter import TwitterToolkit

# Replace the values with your actual twitter access token
consumer_key = ""
consumer_secret = ""


bearer_token = ""
access_token = ""
access_token_secret = ""


# Initialize the Twitter toolkit
twitter_toolkit = TwitterToolkit(bearer_token, consumer_key, consumer_secret, access_token, access_token_secret)

# Create an agent with the twitter toolkit
agent = Agent(
    instructions=[
        "Use your tools to interact with Twitter as the authorized user @phidatahq",
        "When asked to create a tweet, generate appropriate content based on the request",
        "Do not actually post tweets unless explicitly instructed to do so",
        "Provide informative responses about the user's timeline and tweets",
        "Respect Twitter's usage policies and rate limits",
    ],
    tools=[twitter_toolkit],
    debug_mode=True,
    show_tool_calls=True,
)


# # Example usage: Retrieve information about a specific user.
agent.print_response("Can you retrieve information about this user https://x.com/phidatahq ", markdown=True)


# # Example usage: Reply To a Tweet

agent.print_response(
    "Can you reply to this post as a general message as to how great this project is:https://x.com/phidatahq/status/1836101177500479547",
    markdown=True,
)


# # Example usage: Get your details
agent.print_response("Can you return my twitter profile?", markdown=True)

# # Example usage: Send a direct message

agent.print_response(
    "Can a send direct message to the user: https://x.com/phidatahq assking you want learn more about them and a link to their community?",
    markdown=True,
)


# # Example usage: Create a new tweet
agent.print_response("Create & post a tweet about the importance of AI ethics", markdown=True)

# Example usage: Get home timeline
agent.print_response("Get my timeline", markdown=True)
