import time
import requests
from typing import Dict, Any
from phi.tools.toolkit import Toolkit
from phi.utils.log import logger


class ZoomTool(Toolkit):
    def __init__(self, account_id: str, client_id: str, client_secret: str, name: str = "zoom_tool"):
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

    def get_access_token(self):
        if self.access_token and time.time() < self.token_expires_at:
            # Token is still valid
            return self.access_token

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "account_credentials", "account_id": self.account_id}
        response = requests.post(self.token_url, headers=headers, data=data, auth=(self.client_id, self.client_secret))

        if response.status_code != 200:
            print(f"Error fetching access token: {response.text}")
            return None

        token_info = response.json()
        self.access_token = token_info["access_token"]
        expires_in = token_info["expires_in"]  # Token validity in seconds
        self.token_expires_at = time.time() + expires_in - 60  # Refresh a minute before expiry

        print("Access token obtained.")
        return self.access_token

    def schedule_meeting(self, topic: str, start_time: str, duration: int) -> Dict[str, Any]:
        token = self.get_access_token()
        if not token:
            print("Unable to obtain access token.")
            return {}

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

        response = requests.post(url, json=data, headers=headers)
        print(f"Response Status Code: {response.status_code}")

        if response.status_code == 401:
            # Token might have expired; try to refresh it
            print("Access token expired, refreshing token...")
            self.access_token = None
            return self.schedule_meeting(topic, start_time, duration)

        response.raise_for_status()
        return response.json()

    def instructions(self) -> str:
        return "Use this tool to schedule and manage Zoom meetings."
