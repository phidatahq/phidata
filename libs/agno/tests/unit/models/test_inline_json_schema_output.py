"""Every provider reads the canonical dict output_schema shape
({"type": "json_schema", "json_schema": {"name", "schema"}}) in the form its API expects."""

import copy

import pytest

from agno.models.message import Message
from agno.utils.models.schema_utils import json_schema_response_format

SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": "string"},
        "address": {"type": "object", "properties": {"zip": {"type": "string"}}},
    },
    "required": ["city"],
}
CANONICAL = json_schema_response_format(SCHEMA, name="Weather")


def test_claude_flattens_the_canonical_shape():
    pytest.importorskip("anthropic")
    from agno.models.anthropic.claude import Claude

    original = copy.deepcopy(CANONICAL)
    output_format = Claude(id="claude-sonnet-4-6")._build_output_format(CANONICAL)

    assert output_format["type"] == "json_schema"
    assert "json_schema" not in output_format
    assert output_format["schema"]["properties"]["city"] == {"type": "string"}
    assert output_format["schema"]["additionalProperties"] is False
    assert output_format["schema"]["properties"]["address"]["additionalProperties"] is False
    assert CANONICAL == original


def test_claude_closes_nested_objects_when_transform_schema_rejects_the_schema():
    pytest.importorskip("anthropic")
    from agno.models.anthropic.claude import Claude

    # An enum-only property makes transform_schema raise, so the fallback walk runs
    schema = {**SCHEMA, "properties": {**SCHEMA["properties"], "tier": {"enum": ["gold", "silver"]}}}
    output_format = Claude(id="claude-sonnet-4-6")._build_output_format(
        json_schema_response_format(schema, name="Weather")
    )

    assert output_format["schema"]["additionalProperties"] is False
    assert output_format["schema"]["properties"]["address"]["additionalProperties"] is False
    assert "additionalProperties" not in output_format["schema"]["properties"]


def test_claude_passes_its_own_flat_shape_through():
    pytest.importorskip("anthropic")
    from agno.models.anthropic.claude import Claude

    flat = {"type": "json_schema", "schema": {**SCHEMA, "additionalProperties": False}}
    assert Claude(id="claude-sonnet-4-6")._build_output_format(flat) is flat


def test_gemini_sends_the_schema_as_response_json_schema():
    pytest.importorskip("google.genai")
    from agno.models.google.gemini import Gemini

    config = Gemini(api_key="test-key").get_request_params(response_format=CANONICAL)["config"]

    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == SCHEMA


def test_gemini_reuse_never_sends_both_schema_fields():
    pytest.importorskip("google.genai")
    from pydantic import BaseModel

    from agno.models.google.gemini import Gemini

    class Weather(BaseModel):
        city: str

    model = Gemini(api_key="test-key", generation_config={})
    model.get_request_params(response_format=Weather)
    config = model.get_request_params(response_format=CANONICAL)["config"]
    assert config.response_schema is None
    assert config.response_json_schema == SCHEMA

    config = model.get_request_params(response_format=Weather)["config"]
    assert config.response_json_schema is None
    assert config.response_schema is not None
    assert model.generation_config == {}


def test_gemini_inline_schema_replaces_a_configured_response_schema():
    pytest.importorskip("google.genai")
    from agno.models.google.gemini import Gemini

    model = Gemini(api_key="test-key", generation_config={"response_schema": {"type": "OBJECT"}})
    config = model.get_request_params(response_format=CANONICAL)["config"]

    assert config.response_schema is None
    assert config.response_json_schema == SCHEMA


def test_gemini_interactions_sends_the_schema_with_a_json_mime_type():
    pytest.importorskip("google.genai")
    from agno.models.google.gemini_interactions import GeminiInteractions

    kwargs = GeminiInteractions(api_key="test-key")._get_request_kwargs(
        [Message(role="user", content="Hi")], response_format=CANONICAL
    )

    assert kwargs["response_format"] == SCHEMA
    assert kwargs["response_mime_type"] == "application/json"


def test_mistral_sends_the_canonical_shape():
    pytest.importorskip("mistralai")
    from agno.models.mistral.mistral import MistralChat

    response_format = MistralChat(id="mistral-small-latest")._get_response_format_param(CANONICAL)

    assert response_format == {"type": "json_schema", "json_schema": {"name": "Weather", "schema": SCHEMA}}


def test_ollama_sends_the_schema_as_format():
    pytest.importorskip("ollama")
    from agno.models.ollama.chat import Ollama

    kwargs = Ollama(id="llama3.2")._prepare_request_kwargs_for_invoke(response_format=CANONICAL)

    assert kwargs["format"] == SCHEMA


def test_openai_responses_flattens_the_canonical_shape():
    pytest.importorskip("openai")
    from agno.models.openai.responses import OpenAIResponses

    params = OpenAIResponses(id="gpt-5.6-luna").get_request_params(response_format=CANONICAL)

    assert params["text"]["format"] == {"type": "json_schema", "name": "Weather", "schema": SCHEMA, "strict": False}


def test_json_mode_prompt_shows_the_plain_schema():
    import json

    from agno.utils.prompts import get_json_output_prompt

    prompt = get_json_output_prompt(CANONICAL)

    assert json.dumps(SCHEMA) in prompt
    assert "json_schema" not in prompt


def test_external_agents_unwrap_the_canonical_shape():
    from agno.agents.base import BaseExternalAgent

    assert BaseExternalAgent._output_json_schema(CANONICAL, "openai") == SCHEMA
