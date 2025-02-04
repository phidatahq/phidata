import json
import pytest
from io import BytesIO
from agno.document.reader.json_reader import JSONReader
from agno.document import Document

@pytest.fixture
def mock_json_file():
    # Create a mock JSON file with content
    json_data = '[{"name": "Document 1", "content": "Some content here"}]'
    mock_file = BytesIO(json_data.encode('utf-8'))  # Mock file with JSON content
    mock_file.name = 'test_upload.json'  # Name the file
    mock_file.content_type = 'application/json'  # Set the content type to JSON
    return mock_file

def test_upload_json_file(mock_json_file):
    """Test uploading a JSON file."""
    # Create a mock reader that simulates reading the file
    reader = JSONReader()

    # Read the contents from the mock JSON file
    file_content = reader.read(mock_json_file)

    # Check if the file content has the expected number of documents
    assert len(file_content) == 1  # Only one document in the mock JSON

    # Check if the first document is an instance of Document
    assert isinstance(file_content[0], Document)

    # Check the document's name
    assert file_content[0].name == "test_upload"  # Extracted name from the file name

    # Check if the document content matches the expected structure
    expected_content = {"name": "Document 1", "content": "Some content here"}
    assert json.loads(file_content[0].content) == expected_content

