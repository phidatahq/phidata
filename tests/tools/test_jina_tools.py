from unittest.mock import patch, Mock
from phi.tools.jina_tools import JinaReaderTools


def test_jina_reader_tools_initialization():
    tools = JinaReaderTools(api_key="test_key")
    assert tools.api_key == "test_key"
    assert str(tools.base_url) == "https://r.jina.ai/"
    assert str(tools.search_url) == "https://s.jina.ai/"


@patch("requests.get")
def test_read_url(mock_get):
    mock_response = Mock()
    mock_response.json.return_value = {"content": "test content"}
    mock_get.return_value = mock_response

    tools = JinaReaderTools(api_key="test_key")
    result = tools.read_url("https://example.com")

    assert result == "{'content': 'test content'}"
    mock_get.assert_called_once_with("https://r.jina.ai/https://example.com", headers=tools._get_headers())


@patch("requests.get")
def test_search_query(mock_get):
    mock_response = Mock()
    mock_response.json.return_value = {"results": ["result1", "result2"]}
    mock_get.return_value = mock_response

    tools = JinaReaderTools(api_key="test_key")
    result = tools.search_query("test query")

    assert result == "{'results': ['result1', 'result2']}"
    mock_get.assert_called_once_with("https://s.jina.ai/test query", headers=tools._get_headers())


@patch("requests.get")
def test_read_url_error(mock_get):
    mock_get.side_effect = Exception("Test error")

    tools = JinaReaderTools(api_key="test_key")
    result = tools.read_url("https://example.com")

    assert result == "Error reading URL: Test error"


@patch("requests.get")
def test_search_query_error(mock_get):
    mock_get.side_effect = Exception("Test error")

    tools = JinaReaderTools(api_key="test_key")
    result = tools.search_query("test query")

    assert result == "Error performing search: Test error"
