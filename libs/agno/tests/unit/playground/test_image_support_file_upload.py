"""
Unit tests for async_router file upload functionality.
"""

import io
from typing import List
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.testclient import TestClient


# Define an EmptyFile class that simulates an empty file without raising on read.
class EmptyFile:
    def __init__(self, content: bytes):
        self.content = content
        self._read_called = False

    def read(self, n=-1):
        # Always return empty bytes. The endpoint will then raise a ValueError.
        if not self._read_called:
            self._read_called = True
            return b""
        return b""

    def seek(self, offset, whence=0):
        pass


# --- Fixtures ---


@pytest.fixture
def mock_agent():
    """Creates a mock agent with minimal attributes required by the router."""
    mock = Mock()
    mock.agent_id = "test_agent_id"
    mock.name = "Test Agent"
    # Assume deep_copy returns self.
    mock.deep_copy = lambda update=None: mock
    # Dummy asynchronous run method.
    mock.arun = AsyncMock(return_value=iter([{"dummy": "response"}]))
    # Set knowledge to None by default
    mock.knowledge = None
    return mock


@pytest.fixture
def test_app(mock_agent):
    """
    Creates a TestClient app with our dummy router.

    This router mimics the expected agent run endpoint used for file uploads.
    """
    router = APIRouter(prefix="/playground")

    @router.post("/agents/{agent_id}/runs")
    async def create_agent_run(
        agent_id: str,
        message: str = Form(...),
        stream: bool = Form(True),
        monitor: bool = Form(False),
        user_id: str = Form(...),
        files: List[UploadFile] = File(None),
    ):
        # Validate any provided files.
        if files:
            for file in files:
                if file.content_type in ["image/jpeg", "image/png", "image/jpg", "image/webp"]:
                    try:
                        content = await file.read()
                        if not content:
                            raise ValueError("Empty file")
                    except Exception:
                        raise HTTPException(status_code=400, detail="Invalid image file")
                else:
                    # Check for knowledge base before processing documents
                    if mock_agent.knowledge is None:
                        raise HTTPException(status_code=404, detail="KnowledgeBase not found")
                    
                    if file.content_type == "application/pdf":
                        try:
                            content = await file.read()
                            if not content:
                                raise ValueError("Empty PDF file")
                        except Exception:
                            raise HTTPException(status_code=400, detail="Invalid pdf file")
                    else:
                        raise HTTPException(status_code=400, detail="Unsupported file type")
        # For simplicity, assume everything else is OK.
        return {"status": "ok", "agent_id": agent_id}

    # Set raise_server_exceptions to False so that HTTPExceptions are returned as responses.
    return TestClient(router, raise_server_exceptions=False)


@pytest.fixture
def mock_image_file():
    """Creates a mock image file (non-empty)."""
    content = b"fake image content"
    file_obj = io.BytesIO(content)
    upload_file = UploadFile(filename="test.jpg", file=file_obj)
    # Set the underlying mutable _headers attribute.
    upload_file._headers = {"content-type": "image/jpeg"}
    return upload_file


@pytest.fixture
def mock_pdf_file():
    """Creates a mock pdf file."""
    content = b"fake pdf content"
    file_obj = io.BytesIO(content)
    upload_file = UploadFile(filename="test.pdf", file=file_obj)
    upload_file._headers = {"content-type": "application/pdf"}
    return upload_file


@pytest.fixture
def mock_agent_with_knowledge(mock_agent):
    """Creates a mock agent with knowledge base enabled."""
    mock_agent.knowledge = Mock()
    return mock_agent


# --- Test Cases ---


def test_single_image_upload(test_app, mock_agent, mock_image_file):
    """Test uploading a single valid image file."""
    data = {
        "message": "What is this image?",
        "stream": "true",
        "monitor": "false",
        "user_id": "test_user",
    }
    # Passing a single image file via the "files" field.
    files = {"files": ("test.jpg", mock_image_file.file, "image/jpeg")}
    response = test_app.post("/playground/agents/test_agent_id/runs", data=data, files=files)
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_multiple_image_upload(test_app, mock_agent):
    """Test uploading multiple image files using the 'files' field."""
    data = {
        "message": "What are these images?",
        "stream": "true",
        "monitor": "false",
        "user_id": "test_user",
    }
    # Pass multiple files under the same field "files"
    files = [
        ("files", ("test0.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
        ("files", ("test1.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
        ("files", ("test2.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
    ]
    response = test_app.post("/playground/agents/test_agent_id/runs", data=data, files=files)
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_mixed_file_upload(test_app, mock_agent_with_knowledge, mock_image_file, mock_pdf_file):
    """Test uploading both an image and a PDF file via the 'files' field."""
    data = {
        "message": "Process these files",
        "stream": "true",
        "monitor": "false",
        "user_id": "test_user",
    }
    files = [
        ("files", ("test.jpg", mock_image_file.file, "image/jpeg")),
        ("files", ("test.pdf", mock_pdf_file.file, "application/pdf")),
    ]
    response = test_app.post("/playground/agents/test_agent_id/runs", data=data, files=files)
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_no_files_upload(test_app):
    """Test a request with no file uploads."""
    data = {
        "message": "Simple message",
        "stream": "true",
        "monitor": "false",
        "user_id": "test_user",
    }
    response = test_app.post("/playground/agents/test_agent_id/runs", data=data)
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_image_upload_without_knowledge(test_app, mock_agent, mock_image_file):
    """Test uploading an image file when knowledge base is not available."""
    data = {
        "message": "What is this image?",
        "stream": "true",
        "monitor": "false",
        "user_id": "test_user",
    }
    files = {"files": ("test.jpg", mock_image_file.file, "image/jpeg")}
    response = test_app.post("/playground/agents/test_agent_id/runs", data=data, files=files)
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_pdf_upload_without_knowledge(test_app, mock_agent, mock_pdf_file):
    """Test uploading a PDF file when knowledge base is not available."""
    data = {
        "message": "Process this PDF",
        "stream": "true",
        "monitor": "false",
        "user_id": "test_user",
    }
    files = {"files": ("test.pdf", mock_pdf_file.file, "application/pdf")}
    response = test_app.post("/playground/agents/test_agent_id/runs", data=data, files=files)
    assert response.status_code == 404
    assert "KnowledgeBase not found" in response.json().get("detail")
