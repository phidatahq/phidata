import time
import requests
import json
from typing import Optional
from phi.tools.toolkit import Toolkit
from phi.utils.log import logger


class ZoomTool(Toolkit):
    def __init__(
        self,
        account_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        name: str = "zoom_tool",
    ):
        """
        Initialize the ZoomTool.

        Args:
            account_id (str): The Zoom account ID for authentication.
            client_id (str): The client ID for authentication.
            client_secret (str): The client secret for authentication.
            name (str): The name of the tool. Defaults to "zoom_tool".
        """
        super().__init__(name)
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret

        self.token_url = "https://zoom.us/oauth/token"
        self.access_token = None
        self.token_expires_at = 0  # Initialize token expiration timestamp

        if not self.account_id or not self.client_id or not self.client_secret:
            logger.error("ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, and ZOOM_CLIENT_SECRET must be set.")

        # Register functions
        self.register(self.schedule_meeting)

    def get_access_token(self) -> str:
        """
        Obtain or refresh the access token for Zoom API.

        Returns:
            A string containing the access token or an empty string if token retrieval fails.
        """
        if self.access_token and time.time() < self.token_expires_at:
            # Token is still valid
            return str(self.access_token)  # Ensure we return a string

        logger.debug("Fetching new access token")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "account_credentials", "account_id": self.account_id}

        try:
            response = requests.post(
                self.token_url, headers=headers, data=data, auth=(self.client_id, self.client_secret)
            )
            response.raise_for_status()

            token_info = response.json()
            self.access_token = token_info["access_token"]
            expires_in = token_info["expires_in"]  # Token validity in seconds
            self.token_expires_at = time.time() + expires_in - 60  # Refresh a minute before expiry

            logger.info("Access token obtained successfully.")
            return str(self.access_token)  # Ensure we return a string
        except requests.RequestException as e:
            logger.error(f"Error fetching access token: {e}")
            return ""  # Return empty string instead of None

    def schedule_meeting(self, topic: str, start_time: str, duration: int) -> str:
        """
        Schedule a new Zoom meeting.

        Args:
            topic (str): The topic or title of the meeting.
            start_time (str): The start time of the meeting in ISO 8601 format.
            duration (int): The duration of the meeting in minutes.

        Returns:
            A JSON-formatted string containing the response from Zoom API with the scheduled meeting details,
            or an error message if the scheduling fails.
        """
        logger.debug(f"Attempting to schedule meeting: {topic}")
        token = self.get_access_token()
        if not token:
            logger.error("Unable to obtain access token.")
            return json.dumps({"error": "Failed to obtain access token"})

        url = "https://api.zoom.us/v2/users/me/meetings"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {
            "topic": topic,
            "type": 2,
            "start_time": start_time,
            "duration": duration,
            "timezone": "UTC",
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": False,
                "watermark": True,
                "audio": "voip",
                "auto_recording": "none",
            },
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            meeting_info = response.json()

            result = {
                "message": "Meeting scheduled successfully!",
                "meeting_id": meeting_info["id"],
                "topic": meeting_info["topic"],
                "start_time": meeting_info["start_time"],
                "duration": meeting_info["duration"],
                "join_url": meeting_info["join_url"],
            }
            logger.info(f"Meeting scheduled successfully. ID: {meeting_info['id']}")
            return json.dumps(result, indent=2)
        except requests.RequestException as e:
            logger.error(f"Error scheduling meeting: {e}")
            return json.dumps({"error": str(e)})

    def instructions(self) -> str:
        """
        Provide instructions for using the ZoomTool.

        Returns:
            A string containing instructions on how to use the ZoomTool.
        """
        return "Use this tool to schedule and manage Zoom meetings. You can schedule meetings by providing a topic, start time, and duration."
