import json
from functools import wraps
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
    def __init__(
        self,
        scopes: List[str],
        spreadsheet_id: Optional[str] = None,
        spreadsheet_range: Optional[str] = None,
        creds: Optional[Credentials] = None,
        creds_path: Optional[str] = None,
        token_path: Optional[str] = None,
        read: bool = True,
        create: bool = False,
        update: bool = False,
    ):
        super().__init__(name="google_tools")
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet_range = spreadsheet_range
        self.creds = creds
        self.scopes = scopes
        self.credentials_path = creds_path
        self.token_path = token_path

        self.read = read
        self.create = create
        self.update = update

        if read:
            self.register(self.read_sheet)
        if create:
            self.register(self.create_sheet)
        if update:
            self.register(self.update_sheet)

    def auth(self) -> None:
        """
        Authenticate with Google Sheets API
        """
        if self.creds and self.creds.valid:
            return
        if not self.scopes:
            raise ValueError("Scopes must be provided")

        token_file = Path(self.token_path or "token.json")
        creds_file = Path(self.credentials_path or "credentials.json")

        if token_file.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_file), self.scopes)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), self.scopes)
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
