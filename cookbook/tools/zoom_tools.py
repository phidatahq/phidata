import os
import time
from phi.utils.log import logger
import requests
from typing import Optional
import json

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.zoom import ZoomTool

# Get environment variables
ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")


class CustomZoomTool(ZoomTool):
    def __init__(
        self,
        account_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        name: str = "zoom_tool",
    ):
        super().__init__(account_id=account_id, client_id=client_id, client_secret=client_secret, name=name)
        self.token_url = "https://zoom.us/oauth/token"
        self.access_token = None
        self.token_expires_at = 0

    def get_access_token(self) -> str:
        """
        Obtain or refresh the access token for Zoom API.
        Returns:
            A string containing the access token or an empty string if token retrieval fails.
        """
        if self.access_token and time.time() < self.token_expires_at:
            return str(self.access_token)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "account_credentials", "account_id": self.account_id}

        try:
            response = requests.post(
                self.token_url, headers=headers, data=data, auth=(self.client_id, self.client_secret)
            )
            response.raise_for_status()

            token_info = response.json()
            self.access_token = token_info["access_token"]
            expires_in = token_info["expires_in"]
            self.token_expires_at = time.time() + expires_in - 60

            # Pass token to parent class
            self._set_parent_token(self.access_token)
            return str(self.access_token)
        except requests.RequestException as e:
            logger.error(f"Error fetching access token: {e}")
            return ""

    def _set_parent_token(self, token: str) -> None:
        """Helper method to set the token in the parent ZoomTool class"""
        self._ZoomTool__access_token = token  # Access private variable of parent

    def schedule_meeting(self, topic: str, start_time: str, duration: int) -> str:
        """
        Override schedule_meeting to maintain JSON format for testing
        """
        response = super().schedule_meeting(topic, start_time, duration)

        try:
            if isinstance(response, str):
                meeting_info = json.loads(response)
            else:
                meeting_info = response

            # Return JSON format for testing compatibility
            result = {
                "message": "Meeting scheduled successfully!",
                "meeting_id": meeting_info.get("meeting_id"),
                "join_url": meeting_info.get("join_url"),
                "start_time": meeting_info.get("start_time"),
            }
            return json.dumps(result, indent=2)
        except (json.JSONDecodeError, AttributeError) as e:
            return json.dumps({"error": "Failed to process meeting information", "details": str(e)})



zoom_tools = CustomZoomTool(account_id=ACCOUNT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)


agent = Agent(
    name="Zoom Meeting Manager",
    agent_id="zoom-meeting-manager",
    model=OpenAIChat(model="gpt-4"),
    tools=[zoom_tools],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
    instructions=[
        "You are an expert at managing Zoom meetings using the Zoom API.",
        "You can:",
        "1. Schedule new meetings (schedule_meeting)",
        "2. Get meeting details (get_meeting)",
        "3. List all meetings (list_meetings)",
        "4. Get upcoming meetings (get_upcoming_meetings)",
        "5. Delete meetings (delete_meeting)",
        "",
        "Guidelines:",
        "- Use ISO 8601 format for dates (e.g., '2024-12-28T10:00:00Z')",
        "- Ensure meeting times are in the future",
        "- Provide meeting details after scheduling (ID, URL, time)",
        "- Handle errors gracefully",
        "- Confirm successful operations",
    ],
    system_message=(
        "You are a helpful Zoom meeting management assistant. "
        "Always verify operations are successful and provide clear, "
        "formatted responses with relevant meeting details."
    ),
)

if __name__ == "__main__":
    # Example usage
    commands = [
        "Schedule a meeting titled 'Team Sync' tomorrow at 2 PM UTC for 45 minutes",
        "List all my scheduled meetings",
        "What meetings do I have coming up?",
    ]

    for command in commands:
        print(f"\nCommand: {command}")
        agent.print_response(command, markdown=True)

    # Interactive mode
    while True:
        try:
            user_input = input("\nEnter a command (or 'quit' to exit): ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break

            agent.print_response(user_input, markdown=True)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
