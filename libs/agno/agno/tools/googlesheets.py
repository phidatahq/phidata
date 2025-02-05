"""
Google Sheets Toolset for interacting with Sheets API

Required Environment Variables:
-----------------------------
- GOOGLE_SHEETS_CLIENT_ID: Google OAuth client ID
- GOOGLE_SHEETS_CLIENT_SECRET: Google OAuth client secret
- GOOGLE_SHEETS_PROJECT_ID: Google Cloud project ID
- GOOGLE_SHEETS_REDIRECT_URI: Google OAuth redirect URI (default: http://localhost)

How to Get These Credentials:
---------------------------
1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Enable APIs and Services"
   - Search for "Google Sheets API"
   - Click "Enable"

4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Go through the OAuth consent screen setup
   - Give it a name and click "Create"
   - You'll receive:
     * Client ID (GOOGLE_SHEETS_CLIENT_ID)
     * Client Secret (GOOGLE_SHEETS_CLIENT_SECRET)
   - The Project ID (GOOGLE_SHEETS_PROJECT_ID) is visible in the project dropdown at the top of the page

5. Set up environment variables:
   Create a .envrc file in your project root with:
   ```
   export GOOGLE_SHEETS_CLIENT_ID=your_client_id_here
   export GOOGLE_SHEETS_CLIENT_SECRET=your_client_secret_here
   export GOOGLE_SHEETS_PROJECT_ID=your_project_id_here
   export GOOGLE_SHEETS_REDIRECT_URI=http://localhost  # Default value
   ```

Alternatively, follow the instructions in the Google Sheets API Quickstart guide:
1: Steps: https://developers.google.com/sheets/api/quickstart/python
2: Save the credentials.json file to the root of the project or update the path in the GoogleSheetsTools class

Note: The first time you run the application, it will open a browser window for OAuth authentication.
A token.json file will be created to store the authentication credentials for future use.
"""

import json
from functools import wraps
from os import getenv
from pathlib import Path
from typing import Any, List, Optional

from agno.tools import Toolkit

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    raise ImportError(
        "`google-api-python-client` `google-auth-httplib2` `google-auth-oauthlib` not installed. Please install using `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`"
    )


def authenticate(func):
    """Decorator to ensure authentication before executing a function."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.creds or not self.creds.valid:
            self.auth()
        return func(self, *args, **kwargs)

    return wrapper


class GoogleSheetsTools(Toolkit):
    SCOPES = {
        "read": "https://www.googleapis.com/auth/spreadsheets.readonly",
        "write": "https://www.googleapis.com/auth/spreadsheets",
    }

    def __init__(
        self,
        scopes: Optional[List[str]] = None,
        spreadsheet_id: Optional[str] = None,
        spreadsheet_range: Optional[str] = None,
        creds: Optional[Credentials] = None,
        creds_path: Optional[str] = None,
        token_path: Optional[str] = None,
        read: bool = True,
        create: bool = False,
        update: bool = False,
        duplicate: bool = False,
    ):
        super().__init__(name="google_tools")
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet_range = spreadsheet_range
        self.creds = creds
        self.credentials_path = creds_path
        self.token_path = token_path

        if scopes is None:
            if create or update:
                self.scopes = [self.SCOPES["write"]]
            else:
                self.scopes = [self.SCOPES["read"]]
        else:
            self.scopes = scopes

        if (create or update) and self.SCOPES["write"] not in self.scopes:
            raise ValueError("Write operations require the spreadsheets scope")

        if read:
            self.register(self.read_sheet)
        if create:
            self.register(self.create_sheet)
        if update:
            self.register(self.update_sheet)
        if duplicate:
            self.register(self.create_duplicate_sheet)

    def auth(self) -> None:
        """
        Authenticate with Google Sheets API
        """
        if self.creds and self.creds.valid:
            return

        token_file = Path(self.token_path or "token.json")
        creds_file = Path(self.credentials_path or "credentials.json")

        if token_file.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_file), self.scopes)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                client_config = {
                    "installed": {
                        "client_id": getenv("GOOGLE_SHEETS_CLIENT_ID"),
                        "client_secret": getenv("GOOGLE_SHEETS_CLIENT_SECRET"),
                        "project_id": getenv("GOOGLE_SHEETS_PROJECT_ID"),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [getenv("GOOGLE_SHEETS_REDIRECT_URI", "http://localhost")],
                    }
                }
                if creds_file.exists():
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), self.scopes)
                else:
                    flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
                self.creds = flow.run_local_server(port=0)
            token_file.write_text(self.creds.to_json()) if self.creds else None

    @authenticate
    def read_sheet(self, spreadsheet_id: Optional[str] = None, spreadsheet_range: Optional[str] = None) -> str:
        """
        Read values from a Google Sheet. Prioritizes instance attributes over method parameters.

        Args:
            spreadsheet_id: Fallback spreadsheet ID if instance attribute is None
            spreadsheet_range: Fallback range if instance attribute is None

        Returns:
            JSON of list of rows, where each row is a list of values
        """
        if not self.creds:
            return "Not authenticated. Call auth() first."

        # Prioritize instance attributes
        sheet_id = self.spreadsheet_id or spreadsheet_id
        sheet_range = self.spreadsheet_range or spreadsheet_range

        if not sheet_id or not sheet_range:
            return "Spreadsheet ID and range must be provided either in constructor or method call"

        try:
            service = build("sheets", "v4", credentials=self.creds)
            sheet = service.spreadsheets()

            result = sheet.values().get(spreadsheetId=sheet_id, range=sheet_range).execute()
            return json.dumps(result.get("values", []))

        except Exception as e:
            return f"Error reading Google Sheet: {e}"

    @authenticate
    def create_sheet(self, title: str) -> str:
        """
        Create a Google Sheet with a given title.

        Args:
            title: The title of the Google Sheet

        Returns:
            The ID of the created Google Sheet
        """
        if not self.creds:
            return "Not authenticated. Call auth() first."

        try:
            service = build("sheets", "v4", credentials=self.creds)
            spreadsheet = {"properties": {"title": title}}

            spreadsheet = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
            spreadsheet_id = spreadsheet.get("spreadsheetId")

            return f"Spreadsheet created: https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        except Exception as e:
            return f"Error creating Google Sheet: {e}"

    @authenticate
    def update_sheet(
        self, data: List[List[Any]], spreadsheet_id: Optional[str] = None, range_name: Optional[str] = None
    ) -> str:
        """Updates a Google Sheet with the provided data.

        Note: This function can overwrite existing data in the sheet.
        User needs to ensure that the provided range correctly matches the data that needs to be updated.

        Args:
            data: The data to update the sheet with
            spreadsheet_id: The ID of the Google Sheet
            range_name: The range of the Google Sheet to update

        Returns:
            A message indicating the success or failure of the operation
        """
        if not self.creds:
            return "Not authenticated. Call auth() first."

        try:
            service = build("sheets", "v4", credentials=self.creds)

            # Define the request body
            body = {"values": data}

            # Update the sheet
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            ).execute()

            return f"Sheet updated successfully: {spreadsheet_id}"

        except Exception as e:
            return f"Error updating Google Sheet: {e}"

    @authenticate
    def create_duplicate_sheet(self, source_id: str, new_title: Optional[str] = None) -> str:
        """
        Create a new Google Sheet that duplicates an existing one.

        Args:
            source_id: The ID of the source spreadsheet to duplicate
            new_title: Optional new title (defaults to "Copy of [original title]")

        Returns:
            The ID of the created Google Sheet
        """
        if not self.creds:
            return "Not authenticated. Call auth() first."

        try:
            service = build("sheets", "v4", credentials=self.creds)

            # Get the source spreadsheet to copy its properties
            source = service.spreadsheets().get(spreadsheetId=source_id).execute()

            if not new_title:
                new_title = f"{source['properties']['title']}"

            body = {"properties": {"title": new_title}, "sheets": source["sheets"]}

            # Create new spreadsheet with copied properties
            spreadsheet = service.spreadsheets().create(body=body, fields="spreadsheetId").execute()

            spreadsheet_id = spreadsheet.get("spreadsheetId")

            # Copy the data from source to new spreadsheet
            for sheet in source["sheets"]:
                range_name = sheet["properties"]["title"]

                # Get data from source
                result = service.spreadsheets().values().get(spreadsheetId=source_id, range=range_name).execute()
                values = result.get("values", [])

                if values:
                    # Copy to new spreadsheet
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id, range=range_name, valueInputOption="RAW", body={"values": values}
                    ).execute()

            return f"Spreadsheet created: https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        except Exception as e:
            return f"Error creating duplicate Google Sheet: {e}"
