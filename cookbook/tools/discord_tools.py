"""Run `pip install discord.py` to install dependencies."""

import os
from phi.agent import Agent
from phi.tools.discord_tools import DiscordTools
from phi.model.openai import OpenAIChat

discord_token = os.getenv("DISCORD_BOT_TOKEN")
if not discord_token:
    raise ValueError("DISCORD_BOT_TOKEN not set")

# Initialize the Discord toolkit
discord_tools = DiscordTools(
    bot_token=discord_token,
    enable_messaging=True,
    enable_history=True,
    enable_channel_management=True,
)

# Create an agent with the discord toolkit
discord_agent = Agent(
    name="Discord Agent",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "Use your tools to interact with Discord channels and servers",
        "When asked to send a message, generate appropriate content based on the request",
        "Do not send messages unless explicitly instructed to do so",
        "Provide informative responses about channels and servers",
        "Respect Discord's usage policies",
    ],
    tools=[discord_tools],
    show_tool_calls=True,
    markdown=True,
)

# Example 1: Send a message to a channel
discord_agent.print_response("Send a message 'Hello from Phi!' to the channel with ID 123456789")

# Example 2: Get channel information
discord_agent.print_response("Get information about the channel with ID 123456789")

# Example 3: List all channels in a server
discord_agent.print_response("List all channels in the server with ID 987654321")

# Example 4: Get message history from a channel
discord_agent.print_response("Get the last 10 messages from the channel with ID 123456789")

# Note: Make sure to replace the channel IDs and server IDs with actual IDs from your Discord server
# Note: The bot needs appropriate permissions in the Discord server to perform these actions
