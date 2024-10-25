"""Run `pip install discord.py` to install dependencies."""

from phi.agent import Agent
from phi.tools.discord_tools import DiscordTools

# Export the DISCORD_BOT_TOKEN environment variable or provide it directly
# - DISCORD_BOT_TOKEN

# Initialize the Discord toolkit
discord_tools = DiscordTools(
    bot_token="your-bot-token",  # Replace with your Discord bot token
    enable_messaging=True,
    enable_history=True,
    enable_channel_management=True,
)

# Create an agent with the discord toolkit
agent = Agent(
    instructions=[
        "Use your tools to interact with Discord channels and servers",
        "When asked to send a message, generate appropriate content based on the request",
        "Do not send messages unless explicitly instructed to do so",
        "Provide informative responses about channels and servers",
        "Respect Discord's usage policies",
    ],
    tools=[discord_tools],
    show_tool_calls=True,
)

# Example 1: Send a message to a channel
agent.print_response("Send a message 'Hello from Phi!' to the channel with ID 123456789", markdown=True)

# Example 2: Get channel information
agent.print_response("Get information about the channel with ID 123456789", markdown=True)

# Example 3: List all channels in a server
agent.print_response("List all channels in the server with ID 987654321", markdown=True)

# Example 4: Get message history from a channel
agent.print_response("Get the last 10 messages from the channel with ID 123456789", markdown=True)

# Note: Make sure to replace the channel IDs and server IDs with actual IDs from your Discord server
# Note: The bot needs appropriate permissions in the Discord server to perform these actions
