"""
Gmail Toolset for interacting with Gmail API
This toolset requires the following environment variables:
- GMAIL_CLIENT_ID: Google OAuth client ID
- GMAIL_CLIENT_SECRET: Google OAuth client secret
- GMAIL_PROJECT_ID: Google Cloud project ID
- GMAIL_REDIRECT_URI: Google OAuth redirect URI (default: http://localhost)

Set these environment variables in a .env file in the root directory of your project.

You can obtain these values from the Google Cloud Console:
https://console.cloud.google.com/apis/credentials
"""
import os
import base64
from datetime import datetime, timedelta
from typing import List, Optional

from phi.tools import Toolkit

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from email.mime.text import MIMEText

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.modify',
          'https://www.googleapis.com/auth/gmail.compose']

class GmailTools(Toolkit):
    def __init__(self):
        """Initialize GmailTools and authenticate with Gmail API"""
        super().__init__()
        self.creds = self._authenticate()
        self.service = build('gmail', 'v1', credentials=self.creds)
        self.register(self.get_latest_emails)
        self.register(self.get_emails_from_user)
        self.register(self.get_unread_emails)
        self.register(self.get_starred_emails)
        self.register(self.get_emails_by_context)
        self.register(self.get_emails_by_date)
        self.register(self.create_draft_email)
        self.register(self.send_email)
        self.register(self.search_emails)

    def _format_emails(self, emails: List[dict]) -> str:
        """Format list of email dictionaries into a readable string"""
        if not emails:
            return "No emails found"
            
        formatted_emails = []
        for email in emails:
            formatted_email = (
                f"From: {email['from']}\n"
                f"Subject: {email['subject']}\n"
                f"Date: {email['date']}\n"
                f"Body: {email['body']}\n"
                "----------------------------------------"
            )
            formatted_emails.append(formatted_email)
            
        return "\n\n".join(formatted_emails)

    def get_latest_emails(self, count: int) -> str:
        """
        Get the latest X emails from the user's inbox.

        Args:
            count (int): Number of latest emails to retrieve

        Returns:
            str: Formatted string containing email details
        """
        try:
            results = self.service.users().messages().list(
                userId='me', maxResults=count).execute()
            emails = self._get_message_details(results.get('messages', []))
            return self._format_emails(emails)
        except HttpError as error:
            return f"Error retrieving latest emails: {error}"
        except Exception as error:
            return f"Unexpected error retrieving latest emails: {type(error).__name__}: {error}"

    def get_emails_from_user(self, user: str, count: int) -> str:
        """
        Get X number of emails from a specific user (name or email).

        Args:
            user (str): Name or email address of the sender
            count (int): Maximum number of emails to retrieve

        Returns:
            str: Formatted string containing email details
        """
        try:
            query = f'from:{user}' if '@' in user else f'from:{user}*'
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=count).execute()
            emails = self._get_message_details(results.get('messages', []))
            return self._format_emails(emails)
        except HttpError as error:
            return f"Error retrieving emails from {user}: {error}"
        except Exception as error:
            return f"Unexpected error retrieving emails from {user}: {type(error).__name__}: {error}"

    def get_unread_emails(self, count: int) -> str:
        """
        Get the X number of latest unread emails from the user's inbox.

        Args:
            count (int): Maximum number of unread emails to retrieve

        Returns:
            str: Formatted string containing email details
        """
        try:
            results = self.service.users().messages().list(
                userId='me', q='is:unread', maxResults=count).execute()
            emails = self._get_message_details(results.get('messages', []))
            return self._format_emails(emails)
        except HttpError as error:
            return f"Error retrieving unread emails: {error}"
        except Exception as error:
            return f"Unexpected error retrieving unread emails: {type(error).__name__}: {error}"

    def get_starred_emails(self, count: int) -> str:
        """
        Get X number of starred emails from the user's inbox.

        Args:
            count (int): Maximum number of starred emails to retrieve

        Returns:
            str: Formatted string containing email details
        """
        try:
            results = self.service.users().messages().list(
                userId='me', q='is:starred', maxResults=count).execute()
            emails = self._get_message_details(results.get('messages', []))
            return self._format_emails(emails)
        except HttpError as error:
            return f"Error retrieving starred emails: {error}"
        except Exception as error:
            return f"Unexpected error retrieving starred emails: {type(error).__name__}: {error}"

    def get_emails_by_context(self, context: str, count: int) -> str:
        """
        Get X number of emails matching a specific context or search term.

        Args:
            context (str): Search term or context to match in emails
            count (int): Maximum number of emails to retrieve

        Returns:
            str: Formatted string containing email details
        """
        try:
            results = self.service.users().messages().list(
                userId='me', q=context, maxResults=count).execute()
            emails = self._get_message_details(results.get('messages', []))
            return self._format_emails(emails)
        except HttpError as error:
            return f"Error retrieving emails by context '{context}': {error}"
        except Exception as error:
            return f"Unexpected error retrieving emails by context '{context}': {type(error).__name__}: {error}"

    def get_emails_by_date(self, start_date: int, range_in_days: Optional[int] = None, num_emails: Optional[int] = 10) -> str:
        """
        Get emails based on date range. start_date is an integer representing a unix timestamp

        Args:
            start_date (datetime): Start date for the query
            range_in_days (Optional[int]): Number of days to include in the range (default: None)
            num_emails (Optional[int]): Maximum number of emails to retrieve (default: 10)

        Returns:
            str: Formatted string containing email details
        """
        try:
            start_date_dt = datetime.fromtimestamp(start_date)
            if range_in_days:
                end_date = start_date_dt + timedelta(days=range_in_days)
                query = f'after:{start_date_dt.strftime("%Y/%m/%d")} before:{end_date.strftime("%Y/%m/%d")}'
            else:
                query = f'after:{start_date_dt.strftime("%Y/%m/%d")}'
                
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=num_emails).execute()
            emails = self._get_message_details(results.get('messages', []))
            return self._format_emails(emails)
        except HttpError as error:
            return f"Error retrieving emails by date: {error}"
        except Exception as error:
            return f"Unexpected error retrieving emails by date: {type(error).__name__}: {error}"

    def create_draft_email(self, to: str, subject: str, body: str, cc: Optional[str] = None) -> dict:
        """
        Create and save a draft email. to and cc are comma separated string of email ids
        Args:
            to (str): Comma separated string of recipient email addresses
            subject (str): Email subject
            body (str): Email body content
            cc (Optional[str]): Comma separated string of CC email addresses (optional)

        Returns:
            dict: Draft email details including id
        """
        message = self._create_message(to.split(','), subject, body, cc.split(',') if cc else None)
        draft = {'message': message}
        draft = self.service.users().drafts().create(
            userId='me', body=draft).execute()
        return draft

    def send_email(self, to: str, subject: str, body: str, cc: Optional[str] = None) -> dict:
        """
        Send an email immediately. to and cc are comma separated string of email ids
        Args:
            to (str): Comma separated string of recipient email addresses
            subject (str): Email subject
            body (str): Email body content
            cc (Optional[str]): Comma separated string of CC email addresses (optional)

        Returns:
            dict: Sent email details including id
        """
        message = self._create_message(to.split(','), subject, body, cc.split(',') if cc else None)
        message = self.service.users().messages().send(
            userId='me', body=message).execute()
        return message
    
    def search_emails(self, query: str, count: int) -> str:
        """
        Get X number of emails based on a given natural text query.
        Searches in to, from, cc, subject and email body contents.

        Args:
            query (str): Natural language query to search for
            count (int): Number of emails to retrieve

        Returns:
            str: Formatted string containing email details
        """
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=count).execute()
            emails = self._get_message_details(results.get('messages', []))
            return self._format_emails(emails)
        except HttpError as error:
            return f"Error retrieving emails with query '{query}': {error}"
        except Exception as error:
            return f"Unexpected error retrieving emails with query '{query}': {type(error).__name__}: {error}"

    def _authenticate(self) -> Credentials:
        """Authenticate and return Gmail API credentials"""
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                client_config = {
                    "installed": {
                        "client_id": os.getenv("GMAIL_CLIENT_ID"),
                        "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
                        "project_id": os.getenv("GMAIL_PROJECT_ID"),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [os.getenv("GMAIL_REDIRECT_URI", "http://localhost")]
                    }
                }
                flow = InstalledAppFlow.from_client_config(
                    client_config, SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def _create_message(self, to: List[str], subject: str, body: str, cc: Optional[List[str]] = None) -> dict:
        """Create email message"""
        message = MIMEText(body)
        message['to'] = ', '.join(to)
        message['from'] = 'me'
        message['subject'] = subject
        if cc:
            message['cc'] = ', '.join(cc)
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

    def _get_message_details(self, messages: List[dict]) -> List[dict]:
        """Get details for list of messages"""
        details = []
        for msg in messages:
            msg_data = self.service.users().messages().get(
                userId='me', id=msg['id'], format='full').execute()
            details.append({
                'id': msg_data['id'],
                'subject': next((header['value'] for header in msg_data['payload']['headers']
                                 if header['name'] == 'Subject'), None),
                'from': next((header['value'] for header in msg_data['payload']['headers']
                             if header['name'] == 'From'), None),
                'date': next((header['value'] for header in msg_data['payload']['headers']
                             if header['name'] == 'Date'), None),
                'body': self._get_message_body(msg_data)
            })
        return details

    def _get_message_body(self, msg_data: dict) -> str:
        """Extract message body from message data"""
        body = ""
        attachments = []
        try:
            if 'parts' in msg_data['payload']:
                for part in msg_data['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            body = base64.urlsafe_b64decode(part['body']['data']).decode()
                    elif 'filename' in part:
                        attachments.append(part['filename'])
            elif 'body' in msg_data['payload'] and 'data' in msg_data['payload']['body']:
                body = base64.urlsafe_b64decode(msg_data['payload']['body']['data']).decode()
        except Exception:
            return "Unable to decode message body"
        
        if attachments:
            return f"{body}\n\nAttachments: {', '.join(attachments)}"
        return body