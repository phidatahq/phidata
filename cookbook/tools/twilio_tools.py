from phi.agent import Agent
from phi.tools.twilio import TwilioTools
from phi.model.openai import OpenAIChat

"""
Example showing how to use the Twilio Tools with Phi.

Requirements:
- Twilio Account SID and Auth Token (get from console.twilio.com)
- A Twilio phone number
- pip install twilio

Usage:
- Set the following environment variables:
    export TWILIO_ACCOUNT_SID="your_account_sid"
    export TWILIO_AUTH_TOKEN="your_auth_token"

- Or provide them when creating the TwilioTools instance
"""


agent = Agent(
    name="Twilio Agent",
    instructions=[
        """You can help users by:
        - Sending SMS messages
        - Checking message history
        - getting call details
        
        Always confirm before sending messages."""
    ],
    model=OpenAIChat(id="gpt-4o"),
    tools=[TwilioTools()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Can you send an SMS saying 'Your package has arrived' to +1234567890?")
