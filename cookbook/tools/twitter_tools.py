from phi.agent import Agent
from phi.tools.twitter import TwitterToolkit

# Replace the values with your actual twitter access token
consumer_key = "8oyvnHynMXL1SE7aL0iHhENkB"
consumer_secret = "FS4MBGdfgRQJ5WpoNp0h2lakeP87nor9Oq224RxMIlPs7s1hCO"


bearer_token = (
    "AAAAAAAAAAAAAAAAAAAAAN%2FisQEAAAAAVailBKZqW8sDPweEqIma44ChXts%3DU0SfYQYFYCwIhP5OpRAw58F3kpc2OnYbjalDaQh7iXXcTQSYFn"
)
access_token = "746022368041021441-UsSAI0GrObZkfVJXD6jOMwwM60V9ll8"
access_token_secret = "3yh9KXfPkAiK7GWR6ozSetA4k3X4tY4JrKJZpVXPT6f0l"


# Initialize the Twitter toolkit
twitter_toolkit = TwitterToolkit(bearer_token, consumer_key, consumer_secret, access_token, access_token_secret)

# Create an agent with the twitter toolkit
agent = Agent(
    instructions=[
        "Use your tools to interact with Twitter as the authorized user @pritisinghhhh",
        "When asked to create a tweet, generate appropriate content based on the request",
        "Do not actually post tweets unless explicitly instructed to do so",
        "Provide informative responses about the user's timeline and tweets",
        "Respect Twitter's usage policies and rate limits",
    ],
    tools=[twitter_toolkit],
    debug_mode=True,
    show_tool_calls=True,
)

# Example usage: Get home timeline
# agent.print_response("Get my user information", markdown=True)

# # Example usage: Reply To a Tweet

agent.print_response(
    "Can you reply to this post as a general message as to how great this project is:https://x.com/phidatahq/status/1836101177500479547",
    markdown=True,
)


agent.print_response(
    "Can you reply to this post as a general message as to how great this project is:https://x.com/phidatahq/status/1836101177500479547 and you would love to learn more about them",
    markdown=True,
)


# # Example usage: Get your details
agent.print_response("Can you return my twitter profile?", markdown=True)

# # Example usage: Send a direct message

agent.print_response(
    "Can a send direct message to the user: https://x.com/DivitModi saying If you're seeing this, it's sent from my AI assistant as a part of learning",
    markdown=True,
)

agent.print_response(
    "Can a send direct message to the user: https://x.com/phidatahq assking you want learn more about them and a link to their community?",
    markdown=True,
)


# # Example usage: Create a new tweet
agent.print_response("Create a tweet about the importance of AI ethics", markdown=True)

# # Example usage: Retrieve information about a specific user.
agent.print_response("https://x.com/phidatahq ", markdown=True)
