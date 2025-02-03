"""Unit tests for GmailTools class."""

import base64
import json
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest
from google.oauth2.credentials import Credentials

from agno.tools.gmail import GmailTools


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth2 credentials."""
    mock_creds = Mock(spec=Credentials)
    mock_creds.valid = True
    mock_creds.expired = False
    return mock_creds


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def gmail_tools(mock_credentials, mock_gmail_service):
    """Create GmailTools instance with mocked dependencies."""
    with patch("agno.tools.gmail.build") as mock_build:
        mock_build.return_value = mock_gmail_service
        with patch.object(GmailTools, "_authenticate") as mock_auth:
            mock_auth.return_value = mock_credentials
            tools = GmailTools()
            return tools


def create_mock_message(msg_id: str, subject: str, sender: str, date: str, body: str) -> Dict[str, Any]:
    """Helper function to create mock message data."""
    return {
        "id": msg_id,
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": date}
            ],
            "body": {
                "data": base64.urlsafe_b64encode(body.encode()).decode()
            }
        }
    }


def test_get_latest_emails(gmail_tools, mock_gmail_service):
    """Test getting latest emails."""
    # Mock response data
    mock_messages = {
        "messages": [{"id": "123"}, {"id": "456"}]
    }
    mock_message_data = create_mock_message(
        "123", "Test Subject", "sender@test.com", "2024-01-01", "Test body"
    )
    
    # Set up mock returns
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_latest_emails(count=2)
    
    assert "Test Subject" in result
    assert "sender@test.com" in result
    assert "Test body" in result


def test_get_emails_from_user(gmail_tools, mock_gmail_service):
    """Test getting emails from specific user."""
    mock_messages = {
        "messages": [{"id": "123"}]
    }
    mock_message_data = create_mock_message(
        "123", "From User", "specific@test.com", "2024-01-01", "Specific message"
    )
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_emails_from_user("specific@test.com", count=1)
    
    assert "From User" in result
    assert "specific@test.com" in result


def test_get_unread_emails(gmail_tools, mock_gmail_service):
    """Test getting unread emails."""
    mock_messages = {
        "messages": [{"id": "123"}]
    }
    mock_message_data = create_mock_message(
        "123", "Unread Email", "sender@test.com", "2024-01-01", "Unread content"
    )
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_unread_emails(count=1)
    
    assert "Unread Email" in result
    assert "Unread content" in result


def test_get_starred_emails(gmail_tools, mock_gmail_service):
    """Test getting starred emails."""
    mock_messages = {
        "messages": [{"id": "123"}]
    }
    mock_message_data = create_mock_message(
        "123", "Starred Email", "sender@test.com", "2024-01-01", "Starred content"
    )
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_starred_emails(count=1)
    
    assert "Starred Email" in result
    assert "Starred content" in result


def test_get_emails_by_context(gmail_tools, mock_gmail_service):
    """Test getting emails by context."""
    mock_messages = {
        "messages": [{"id": "123"}]
    }
    mock_message_data = create_mock_message(
        "123", "Context Email", "sender@test.com", "2024-01-01", "Contextual content"
    )
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_emails_by_context("test context", count=1)
    
    assert "Context Email" in result
    assert "Contextual content" in result


def test_get_emails_by_date(gmail_tools, mock_gmail_service):
    """Test getting emails by date."""
    mock_messages = {
        "messages": [{"id": "123"}]
    }
    mock_message_data = create_mock_message(
        "123", "Date Email", "sender@test.com", "2024-01-01", "Date-specific content"
    )
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    start_date = int(datetime(2024, 1, 1).timestamp())
    result = gmail_tools.get_emails_by_date(start_date, range_in_days=1)
    
    assert "Date Email" in result
    assert "Date-specific content" in result


def test_create_draft_email(gmail_tools, mock_gmail_service):
    """Test creating draft email."""
    mock_draft_response = {
        "id": "draft123",
        "message": {"id": "msg123"}
    }
    
    mock_gmail_service.users().drafts().create().execute.return_value = mock_draft_response
    
    result = gmail_tools.create_draft_email(
        to="recipient@test.com",
        subject="Test Draft",
        body="Draft content",
        cc="cc@test.com"
    )
    
    assert "draft123" in result
    assert "msg123" in result


def test_send_email(gmail_tools, mock_gmail_service):
    """Test sending email."""
    mock_send_response = {
        "id": "msg123",
        "labelIds": ["SENT"]
    }
    
    mock_gmail_service.users().messages().send().execute.return_value = mock_send_response
    
    result = gmail_tools.send_email(
        to="recipient@test.com",
        subject="Test Send",
        body="Email content",
        cc="cc@test.com"
    )
    
    assert "msg123" in result


def test_search_emails(gmail_tools, mock_gmail_service):
    """Test searching emails."""
    mock_messages = {
        "messages": [{"id": "123"}]
    }
    mock_message_data = create_mock_message(
        "123", "Search Result", "sender@test.com", "2024-01-01", "Searchable content"
    )
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.search_emails("search query", count=1)
    
    assert "Search Result" in result
    assert "Searchable content" in result


def test_error_handling(gmail_tools, mock_gmail_service):
    """Test error handling in Gmail tools."""
    from googleapiclient.errors import HttpError
    
    # Mock an HTTP error
    mock_gmail_service.users().messages().list.side_effect = HttpError(
        resp=Mock(status=403), content=b'{"error": {"message": "Access Denied"}}'
    )
    
    result = gmail_tools.get_latest_emails(count=1)
    assert "Error retrieving latest emails" in result


def test_message_with_attachments(gmail_tools, mock_gmail_service):
    """Test handling messages with attachments."""
    mock_messages = {
        "messages": [{"id": "123"}]
    }
    mock_message_data = {
        "id": "123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "With Attachment"},
                {"name": "From", "value": "sender@test.com"},
                {"name": "Date", "value": "2024-01-01"}
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode("Message with attachment".encode()).decode()
                    }
                },
                {
                    "filename": "test.pdf",
                    "mimeType": "application/pdf"
                }
            ]
        }
    }
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_latest_emails(count=1)
    
    assert "With Attachment" in result
    assert "Message with attachment" in result
    assert "test.pdf" in result


def test_empty_message_list(gmail_tools, mock_gmail_service):
    """Test handling of empty message list."""
    mock_messages = {"messages": []}
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    
    result = gmail_tools.get_latest_emails(count=1)
    assert "No emails found" in result


def test_malformed_message(gmail_tools, mock_gmail_service):
    """Test handling of malformed message data."""
    mock_messages = {"messages": [{"id": "123"}]}
    mock_message_data = {
        "id": "123",
        "payload": {
            "headers": []  # Missing required headers
        }
    }
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_latest_emails(count=1)
    assert result  # Should handle missing headers gracefully


def test_network_error(gmail_tools, mock_gmail_service):
    """Test handling of network errors."""
    mock_gmail_service.users().messages().list.side_effect = ConnectionError("Network unavailable")
    
    result = gmail_tools.get_latest_emails(count=1)
    assert "Error" in result


def test_html_message_content(gmail_tools, mock_gmail_service):
    """Test handling of HTML message content."""
    mock_messages = {"messages": [{"id": "123"}]}
    html_content = "<p>HTML content</p>"
    mock_message_data = {
        "id": "123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "HTML Email"},
                {"name": "From", "value": "sender@test.com"},
                {"name": "Date", "value": "2024-01-01"}
            ],
            "mimeType": "text/html",
            "body": {
                "data": base64.urlsafe_b64encode(html_content.encode()).decode()
            }
        }
    }
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_latest_emails(count=1)
    
    # Verify email metadata
    assert "HTML Email" in result
    assert "sender@test.com" in result
    
    # Verify HTML content is included in the result
    assert html_content in result or base64.urlsafe_b64decode(mock_message_data["payload"]["body"]["data"]).decode() in result


def test_multiple_recipients(gmail_tools, mock_gmail_service):
    """Test sending email to multiple recipients."""
    mock_send_response = {
        "id": "msg123",
        "labelIds": ["SENT"]
    }
    
    mock_gmail_service.users().messages().send().execute.return_value = mock_send_response
    
    result = gmail_tools.send_email(
        to="recipient1@test.com,recipient2@test.com",
        subject="Multiple Recipients",
        body="Test content"
    )
    
    assert "msg123" in result


def test_rate_limit_error(gmail_tools, mock_gmail_service):
    """Test handling of rate limit errors."""
    from googleapiclient.errors import HttpError
    
    mock_gmail_service.users().messages().list.side_effect = HttpError(
        resp=Mock(status=429), 
        content=b'{"error": {"message": "Rate limit exceeded"}}'
    )
    
    result = gmail_tools.get_latest_emails(count=1)
    assert "Error retrieving latest emails" in result


def test_multipart_complex_message(gmail_tools, mock_gmail_service):
    """Test handling of complex multipart messages."""
    mock_messages = {"messages": [{"id": "123"}]}
    mock_message_data = {
        "id": "123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Complex Message"},
                {"name": "From", "value": "sender@test.com"},
                {"name": "Date", "value": "2024-01-01"}
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode("Plain text version".encode()).decode()
                    }
                },
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode("<p>HTML version</p>".encode()).decode()
                    }
                },
                {
                    "filename": "test.pdf",
                    "mimeType": "application/pdf"
                }
            ]
        }
    }
    
    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data
    
    result = gmail_tools.get_latest_emails(count=1)
    assert "Complex Message" in result
    assert "Plain text version" in result
    assert "test.pdf" in result


def test_invalid_email_parameters(gmail_tools):
    """Test handling of invalid email parameters."""
    with pytest.raises(Exception):  # Should raise an appropriate exception
        gmail_tools.send_email(
            to="invalid-email",  # Invalid email format
            subject="",  # Empty subject
            body=None  # None body
        ) 