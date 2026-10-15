"""Unit tests for OlostepTools.

The real Olostep SDK client is used, with a fake transport in place of the network.
That way the tests check the keyword arguments the SDK accepts and the shape of the
objects it returns, which plain Mock objects would not catch. No live API calls are made.
"""

import json
import os
from typing import Any, Callable, Dict, List
from unittest.mock import patch

import pytest

# Skip all tests in this module if olostep is not installed
pytest.importorskip("olostep")

from olostep import Olostep, Olostep_BaseError  # noqa: E402
from olostep.backend.transport_protocol import RawAPIRequest, RawAPIResponse  # noqa: E402

from agno.tools.olostep import OlostepTools  # noqa: E402


def _ok(body: Dict[str, Any]) -> RawAPIResponse:
    return RawAPIResponse(200, {"content-type": "application/json"}, json.dumps(body))


class FakeTransport:
    """Answers Olostep API calls with canned responses and records the requests."""

    def __init__(self) -> None:
        self.requests: List[RawAPIRequest] = []
        self.overrides: Dict[str, Callable[[RawAPIRequest], RawAPIResponse]] = {}

    async def request(self, request: RawAPIRequest) -> RawAPIResponse:
        self.requests.append(request)
        path = request.url.split("/v1", 1)[1]
        if path in self.overrides:
            return self.overrides[path](request)
        return self.route(request, path)

    async def close(self) -> None:
        return None

    def bodies(self, path: str) -> List[Dict[str, Any]]:
        return [r.json or {} for r in self.requests if r.url.endswith(f"/v1{path}") and r.method == "POST"]

    def route(self, request: RawAPIRequest, path: str) -> RawAPIResponse:
        body = request.json or {}
        if path == "/scrapes":
            result: Dict[str, Any] = {"markdown_content": "# Test Page\n\nTest content"}
            if "json" in body.get("formats", []):
                result["json_content"] = json.dumps({"title": "Test Page"})
            return _ok(
                {
                    "id": "scrape_1",
                    "object": "scrape",
                    "created": 1,
                    "url": body["url_to_scrape"],
                    "retrieve_id": "ret_scrape",
                    "result": result,
                }
            )
        if path == "/searches":
            return _ok(
                {
                    "id": "search_1",
                    "object": "search",
                    "created": 1,
                    "query": body["query"],
                    "result": {
                        "links": [
                            {
                                "url": "https://example.com",
                                "title": "Example Site",
                                "description": "Example description",
                            },
                            {"url": "https://example.org"},
                        ]
                    },
                }
            )
        if path == "/answers":
            json_content = json.dumps({"company": "Olostep", "founded": "2023"}) if "json_format" in body else "Paris"
            return _ok(
                {
                    "id": "answer_1",
                    "object": "answer",
                    "created": 1,
                    "task": body["task"],
                    "result": {"json_content": json_content, "sources": ["https://example.com", "https://other.com"]},
                }
            )
        if path == "/maps":
            return _ok({"urls_count": 2, "urls": ["https://example.com/page1", "https://example.com/page2"]})
        if path == "/crawls":
            return _ok(self._crawl())
        if path == "/crawls/crawl_1":
            return _ok(self._crawl())
        if path == "/crawls/crawl_1/pages":
            return _ok(
                {
                    "id": "crawl_1",
                    "object": "crawl",
                    "status": "completed",
                    "pages_count": 2,
                    "pages": [
                        {"id": "p1", "retrieve_id": "ret_p1", "url": "https://example.com/page1", "is_external": False},
                        {"id": "p2", "retrieve_id": "ret_p2", "url": "https://example.com/page2", "is_external": False},
                    ],
                    "metadata": {"external_urls": [], "failed_urls": []},
                }
            )
        if path == "/batches":
            return _ok(self._batch())
        if path == "/batches/batch_1":
            return _ok({**self._batch(), "number_retried": 0, "parser": ""})
        if path == "/batches/batch_1/items":
            return _ok(
                {
                    "id": "batch_1",
                    "object": "batch",
                    "status": "completed",
                    "items": [
                        {"custom_id": "a", "retrieve_id": "ret_a", "url": "https://example.com/a"},
                        {"custom_id": "b", "retrieve_id": "ret_b", "url": "https://example.com/b"},
                    ],
                    "items_count": 2,
                }
            )
        if path == "/retrieve":
            retrieve_id = (request.query or {}).get("retrieve_id", "")
            return _ok({"markdown_content": f"# Content for {retrieve_id}"})
        return RawAPIResponse(404, {}, json.dumps({"error": f"unexpected path {path}"}))

    @staticmethod
    def _crawl() -> Dict[str, Any]:
        return {
            "id": "crawl_1",
            "object": "crawl",
            "status": "completed",
            "created": 1,
            "start_date": "2026-01-01",
            "start_url": "https://example.com",
            "include_external": False,
            "pages_count": 2,
        }

    @staticmethod
    def _batch() -> Dict[str, Any]:
        return {
            "id": "batch_1",
            "object": "batch",
            "status": "completed",
            "created": 1,
            "total_urls": 2,
            "completed_urls": 2,
            "start_date": "2026-01-01",
        }


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def make_tools(transport: FakeTransport) -> Callable[..., OlostepTools]:
    def _make(**kwargs: Any) -> OlostepTools:
        tools = OlostepTools(api_key="test_key", **kwargs)
        # `_transport` is an internal SDK argument, used here to avoid network access.
        tools.client = Olostep(api_key="test_key", _transport=transport)
        return tools

    return _make


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def test_init_with_api_key():
    with patch("agno.tools.olostep.Olostep") as mock_olostep_class:
        tools = OlostepTools(api_key="test_key")
    assert tools.api_key == "test_key"
    mock_olostep_class.assert_called_once_with(api_key="test_key")


def test_init_with_env_api_key():
    with (
        patch("agno.tools.olostep.Olostep") as mock_olostep_class,
        patch.dict(os.environ, {"OLOSTEP_API_KEY": "env_key"}),
    ):
        tools = OlostepTools()
    assert tools.api_key == "env_key"
    mock_olostep_class.assert_called_once_with(api_key="env_key")


def test_init_without_api_key_logs_error():
    with (
        patch("agno.tools.olostep.Olostep"),
        patch.dict(os.environ, {}, clear=True),
        patch("agno.tools.olostep.log_error") as mock_log_error,
    ):
        OlostepTools()
    mock_log_error.assert_called_once()


def test_default_registers_only_scrape():
    with patch("agno.tools.olostep.Olostep"):
        tools = OlostepTools(api_key="test_key")
    assert list(tools.functions) == ["scrape_url"]


def test_selective_tools_registered():
    with patch("agno.tools.olostep.Olostep"):
        tools = OlostepTools(api_key="test_key", scrape_url=False, search_web=True, answer_question=True)
    assert sorted(tools.functions) == ["answer_question", "search_web"]


def test_all_tools_registered():
    with patch("agno.tools.olostep.Olostep"):
        tools = OlostepTools(api_key="test_key", all_tools=True)
    assert sorted(tools.functions) == [
        "answer_question",
        "batch_scrape",
        "crawl_website",
        "map_website",
        "scrape_url",
        "search_web",
    ]


def test_toolkit_kwargs_are_passed_through():
    with patch("agno.tools.olostep.Olostep"):
        tools = OlostepTools(api_key="test_key", all_tools=True, exclude_tools=["batch_scrape"])
    assert "batch_scrape" not in tools.functions
    assert "scrape_url" in tools.functions


# ---------------------------------------------------------------------------
# scrape_url
# ---------------------------------------------------------------------------


def test_scrape_url_markdown(make_tools, transport):
    result = make_tools().scrape_url("https://example.com")
    assert result == "# Test Page\n\nTest content"
    body = transport.bodies("/scrapes")[0]
    assert body["formats"] == ["markdown"]
    assert body["url_to_scrape"].startswith("https://example.com")


def test_scrape_url_options_are_sent(make_tools, transport):
    make_tools().scrape_url(
        "https://example.com",
        formats="markdown, html",
        wait_before_scraping=500,
        remove_images=True,
        country="gb",
        parser_id="@olostep/extract-emails",
    )
    body = transport.bodies("/scrapes")[0]
    assert body["formats"] == ["markdown", "html"]
    assert body["wait_before_scraping"] == 500
    assert body["remove_images"] is True
    assert body["country"] == "GB"
    assert body["parser"] == {"id": "@olostep/extract-emails"}


def test_scrape_url_json_content_is_returned_as_string(make_tools):
    result = make_tools().scrape_url("https://example.com", formats="json", llm_extract_schema='{"type": "object"}')
    assert isinstance(result, str)
    assert json.loads(result) == {"title": "Test Page"}


def test_scrape_url_llm_extract_schema_is_sent(make_tools, transport):
    make_tools().scrape_url("https://example.com", formats="json", llm_extract_schema='{"type": "object"}')
    assert transport.bodies("/scrapes")[0]["llm_extract"] == {"schema": {"type": "object"}}


def test_scrape_url_llm_extract_prompt_is_sent(make_tools, transport):
    result = make_tools().scrape_url("https://example.com", formats="json", llm_extract_prompt="Get the title")
    assert transport.bodies("/scrapes")[0]["llm_extract"] == {"prompt": "Get the title"}
    assert json.loads(result) == {"title": "Test Page"}


def test_scrape_url_schema_wins_over_prompt(make_tools, transport):
    make_tools().scrape_url(
        "https://example.com",
        formats="json",
        llm_extract_schema='{"type": "object"}',
        llm_extract_prompt="Get the title",
    )
    assert transport.bodies("/scrapes")[0]["llm_extract"] == {"schema": {"type": "object"}}


def test_scrape_url_invalid_schema(make_tools, transport):
    result = make_tools().scrape_url("https://example.com", formats="json", llm_extract_schema="not json")
    assert result == "Error: llm_extract_schema must be a valid JSON string."
    assert transport.requests == []


def test_scrape_url_requested_format_missing(make_tools, transport):
    # json was requested but the API returned no json_content
    transport.overrides["/scrapes"] = lambda r: _ok(
        {"id": "scrape_1", "object": "scrape", "created": 1, "url": "https://example.com", "result": {}}
    )
    result = make_tools().scrape_url("https://example.com", formats="json")
    assert result == "No content returned for the requested formats."


def test_scrape_url_api_error(make_tools, transport):
    transport.overrides["/scrapes"] = lambda r: RawAPIResponse(
        401, {"content-type": "application/json"}, json.dumps({"error": {"message": "Invalid API key"}})
    )
    result = make_tools().scrape_url("https://example.com")
    assert result.startswith("Olostep API error scraping https://example.com")


def test_scrape_url_unexpected_error(make_tools):
    tools = make_tools()
    with patch.object(tools.client.scrapes, "create", side_effect=RuntimeError("boom")):
        result = tools.scrape_url("https://example.com")
    assert result == "Unexpected error scraping https://example.com: boom"


def test_sdk_error_class_is_importable():
    assert issubclass(Olostep_BaseError, Exception)


# ---------------------------------------------------------------------------
# crawl_website
# ---------------------------------------------------------------------------


def test_crawl_website(make_tools, transport):
    result = json.loads(make_tools(crawl_website=True).crawl_website("https://example.com", max_pages=2))
    assert result == [
        {"url": "https://example.com/page1", "markdown_content": "# Content for ret_p1"},
        {"url": "https://example.com/page2", "markdown_content": "# Content for ret_p2"},
    ]
    body = transport.bodies("/crawls")[0]
    assert body["start_url"].startswith("https://example.com")
    assert body["max_pages"] == 2


def test_crawl_website_with_filters(make_tools, transport):
    make_tools(crawl_website=True).crawl_website(
        "https://example.com",
        max_depth=3,
        include_urls="/blog/**, /docs/**",
        exclude_urls="/admin/**",
        search_query="pricing",
        top_n=5,
    )
    body = transport.bodies("/crawls")[0]
    assert body["max_depth"] == 3
    assert body["include_urls"] == ["/blog/**", "/docs/**"]
    assert body["exclude_urls"] == ["/admin/**"]
    assert body["search_query"] == "pricing"
    assert body["top_n"] == 5


def test_crawl_website_page_without_content(make_tools, transport):
    # a page that comes back with no markdown still shows up in the result
    transport.overrides["/retrieve"] = lambda r: _ok({})
    result = json.loads(make_tools(crawl_website=True).crawl_website("https://example.com"))
    assert [p["markdown_content"] for p in result] == ["", ""]


def test_crawl_website_error(make_tools):
    tools = make_tools(crawl_website=True)
    with patch.object(tools.client.crawls, "create", side_effect=RuntimeError("boom")):
        assert tools.crawl_website("https://example.com") == "Unexpected error crawling https://example.com: boom"


# ---------------------------------------------------------------------------
# map_website
# ---------------------------------------------------------------------------


def test_map_website(make_tools):
    result = json.loads(make_tools(map_website=True).map_website("https://example.com"))
    assert result == ["https://example.com/page1", "https://example.com/page2"]


def test_map_website_with_filters(make_tools, transport):
    make_tools(map_website=True).map_website(
        "https://example.com",
        include_urls="/product, /product/**",
        exclude_urls="/ads/**",
        include_subdomain=True,
        top_n=10,
    )
    body = transport.bodies("/maps")[0]
    assert body["include_urls"] == ["/product", "/product/**"]
    assert body["exclude_urls"] == ["/ads/**"]
    assert body["include_subdomain"] is True
    assert body["top_n"] == 10


# ---------------------------------------------------------------------------
# search_web
# ---------------------------------------------------------------------------


def test_search_web(make_tools, transport):
    result = json.loads(make_tools(search_web=True).search_web("vector databases"))
    assert result == [
        {"url": "https://example.com", "title": "Example Site", "description": "Example description"},
        {"url": "https://example.org", "title": "", "description": ""},
    ]
    assert transport.bodies("/searches")[0] == {"query": "vector databases"}


def test_search_web_no_results(make_tools, transport):
    transport.overrides["/searches"] = lambda r: _ok(
        {"id": "search_1", "object": "search", "created": 1, "query": "q", "result": {"links": []}}
    )
    assert json.loads(make_tools(search_web=True).search_web("q")) == []


# ---------------------------------------------------------------------------
# answer_question
# ---------------------------------------------------------------------------


def test_answer_question(make_tools, transport):
    result = json.loads(make_tools(answer_question=True).answer_question("Capital of France?"))
    assert result == {"answer": "Paris", "sources": ["https://example.com", "https://other.com"]}
    assert "json_format" not in transport.bodies("/answers")[0]


def test_answer_question_with_schema(make_tools, transport):
    schema = {"company": "", "founded": ""}
    result = json.loads(
        make_tools(answer_question=True).answer_question("About Olostep", json_schema=json.dumps(schema))
    )
    assert result == {
        "company": "Olostep",
        "founded": "2023",
        "_sources": ["https://example.com", "https://other.com"],
    }
    assert transport.bodies("/answers")[0]["json_format"] == schema


def test_answer_question_invalid_schema(make_tools, transport):
    result = make_tools(answer_question=True).answer_question("q", json_schema="not json")
    assert result == "Error: json_schema must be a valid JSON string."
    assert transport.requests == []


# ---------------------------------------------------------------------------
# batch_scrape
# ---------------------------------------------------------------------------


def test_batch_scrape(make_tools, transport):
    result = json.loads(make_tools(batch_scrape=True).batch_scrape("https://example.com/a, https://example.com/b"))
    assert result == [
        {"url": "https://example.com/a", "custom_id": "a", "content": "# Content for ret_a"},
        {"url": "https://example.com/b", "custom_id": "b", "content": "# Content for ret_b"},
    ]
    items = transport.bodies("/batches")[0]["items"]
    assert [i["url"].rstrip("/") for i in items] == ["https://example.com/a", "https://example.com/b"]


def test_batch_scrape_with_parser_and_country(make_tools, transport):
    make_tools(batch_scrape=True).batch_scrape(
        "https://example.com/a", formats="json", parser_id="@olostep/google-search", country="us"
    )
    body = transport.bodies("/batches")[0]
    assert body["parser"] == {"id": "@olostep/google-search"}
    assert body["country"] == "US"


def test_batch_scrape_empty_urls(make_tools, transport):
    assert make_tools(batch_scrape=True).batch_scrape(" , ") == "Error: no valid URLs provided."
    assert transport.requests == []


def test_batch_scrape_item_without_content(make_tools, transport):
    transport.overrides["/retrieve"] = lambda r: _ok({})
    result = json.loads(make_tools(batch_scrape=True).batch_scrape("https://example.com/a"))
    assert [r["content"] for r in result] == ["", ""]
