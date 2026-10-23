"""json_schema_to_model builds a Pydantic model that keeps what the JSON Schema says, or refuses."""

import warnings

import pytest
from pydantic import BaseModel, ValidationError

from agno.exceptions import ComponentRehydrationError
from agno.utils.models.json_schema_model import (
    UnsupportedJsonSchemaError,
    json_schema_to_model,
    rehydrate_inline_output_schema,
    serialize_output_schema,
    source_json_schema,
)
from agno.utils.models.schema_utils import json_schema_response_format

TICKET = {
    "title": "Ticket",
    "type": "object",
    "description": "A support ticket",
    "properties": {
        "summary": {"type": "string", "description": "One-line summary", "maxLength": 80},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
        "assignee": {"type": ["string", "null"], "description": "Email, or null if unassigned"},
        "labels": {"type": "object", "additionalProperties": {"type": "string"}},
        "due": {"anyOf": [{"type": "string", "format": "date"}, {"type": "null"}]},
        "owner": {"$ref": "#/$defs/Person"},
        "score": {"type": "integer", "minimum": 1, "maximum": 5},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
    },
    "required": ["summary", "priority", "assignee", "labels", "due", "owner", "score", "tags"],
    "$defs": {
        "Person": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "manager": {"$ref": "#/$defs/Person"}},
            "required": ["name"],
        }
    },
}
VALID = {
    "summary": "Login fails",
    "priority": "high",
    "assignee": None,
    "labels": {"area": "auth"},
    "due": "2026-11-01",
    "owner": {"name": "Ana", "manager": {"name": "Bo"}},
    "score": 4,
    "tags": ["login"],
}


@pytest.fixture(scope="module")
def ticket():
    return json_schema_to_model(TICKET)


def test_the_model_schema_keeps_every_constraint(ticket):
    out = ticket.model_json_schema()
    props = out["properties"]
    assert out["title"] == "Ticket"
    assert out["description"] == "A support ticket"
    assert props["summary"]["description"] == "One-line summary"
    assert props["summary"]["maxLength"] == 80
    assert props["priority"]["enum"] == ["low", "medium", "high"]
    assert props["assignee"]["description"] == "Email, or null if unassigned"
    assert {"type": "null"} in props["assignee"]["anyOf"]
    assert props["labels"]["additionalProperties"] == {"type": "string"}
    assert {"type": "string", "format": "date"} in props["due"]["anyOf"]
    assert props["score"]["minimum"] == 1 and props["score"]["maximum"] == 5
    assert props["tags"]["maxItems"] == 3
    assert sorted(out["required"]) == sorted(TICKET["required"])
    assert "Person" in out["$defs"]


def test_valid_output_validates_including_a_recursive_ref(ticket):
    parsed = ticket.model_validate(VALID)
    assert parsed.owner.manager.name == "Bo"
    assert parsed.assignee is None


@pytest.mark.parametrize(
    "change",
    [
        {"priority": "urgent"},
        {"summary": "x" * 81},
        {"score": 9},
        {"labels": {"area": 3}},
        {"tags": ["a", "b", "c", "d"]},
    ],
    ids=["enum", "maxLength", "maximum", "map-value-type", "maxItems"],
)
def test_output_breaking_the_schema_is_rejected(ticket, change):
    with pytest.raises(ValidationError):
        ticket.model_validate({**VALID, **change})


def test_optional_property_gets_its_default():
    model = json_schema_to_model(
        {"type": "object", "properties": {"a": {"type": "string", "default": "x", "description": "doc"}}}
    )
    assert model.model_validate({}).a == "x"
    assert model.model_json_schema()["properties"]["a"]["description"] == "doc"


def test_property_names_that_are_not_identifiers_work_without_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        model = json_schema_to_model(
            {"type": "object", "properties": {"due-date": {"type": "string"}, "schema": {"type": "string"}}}
        )
    assert model.model_validate({"due-date": "a", "schema": "b"}).model_dump() == {"due-date": "a", "schema": "b"}


def test_oneof_over_distinct_types_is_a_union():
    model = json_schema_to_model(
        {"type": "object", "properties": {"v": {"oneOf": [{"type": "string"}, {"type": "integer"}]}}, "required": ["v"]}
    )
    assert model.model_validate({"v": 3}).v == 3


def test_additional_properties_false_forbids_extra_keys():
    model = json_schema_to_model(
        {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": False}
    )
    with pytest.raises(ValidationError):
        model.model_validate({"a": "x", "b": "y"})


@pytest.mark.parametrize(
    "schema, reason",
    [
        ({"type": "array", "items": {}}, "root must be an object"),
        ({"type": "object", "properties": {"a": {"allOf": [{"type": "string"}, {"maxLength": 2}]}}}, "allOf"),
        ({"type": "object", "properties": {"a": {"not": {"type": "string"}}}}, "unsupported keyword(s): not"),
        ({"type": "object", "properties": {"a": {"type": "object", "patternProperties": {}}}}, "patternProperties"),
        (
            {
                "type": "object",
                "properties": {"a": {"oneOf": [{"type": "string"}, {"type": "string", "maxLength": 2}]}},
            },
            "distinct type",
        ),
        ({"type": "object", "properties": {"a": {"type": "string"}}, "required": ["b"]}, "required lists"),
        (
            {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "additionalProperties": {"type": "string"},
            },
            "schema-valued additionalProperties",
        ),
        ({"type": "object", "properties": {"a": {"$ref": "https://x/schema.json"}}}, "only local refs"),
        ({"type": "object", "properties": {"a": {"$ref": "#/$defs/Missing"}}}, "does not resolve"),
        ({"type": "object", "properties": {"a": {"type": "array", "items": [{"type": "string"}]}}}, "tuple-style"),
        ({"type": "object", "properties": {"_a": {"type": "string"}}}, "property names"),
        ({"type": "object", "properties": {"model_name": {"type": "string"}}}, "property names"),
        ({"type": "object", "properties": {"a": {"enum": [{"x": 1}]}}}, "enum and const values"),
        ({"type": "object", "properties": {"a": {"type": "integer", "maxLength": 3}}}, "needs type string"),
        ({"type": "object", "properties": {"a": {"type": "strin"}}}, "unknown type 'strin'"),
    ],
    ids=[
        "array-root",
        "allOf",
        "not",
        "patternProperties",
        "oneOf-overlapping",
        "required-missing",
        "properties-and-map",
        "remote-ref",
        "missing-ref",
        "tuple-items",
        "underscore-name",
        "model-prefix-name",
        "object-enum",
        "constraint-wrong-type",
        "unknown-type",
    ],
)
def test_unrepresentable_schemas_are_refused(schema, reason):
    with pytest.raises(UnsupportedJsonSchemaError, match=reason.replace("(", r"\(").replace(")", r"\)")):
        json_schema_to_model(schema)


def test_refusals_name_where_they_happened():
    with pytest.raises(UnsupportedJsonSchemaError, match="at properties/outer/properties/inner"):
        json_schema_to_model(
            {
                "type": "object",
                "properties": {"outer": {"type": "object", "properties": {"inner": {"not": {}}}}},
            }
        )


def test_serialize_writes_back_the_source_dict(ticket):
    class Plain(BaseModel):
        a: str

    assert serialize_output_schema(ticket) == TICKET
    assert source_json_schema(ticket) == TICKET
    assert serialize_output_schema(Plain) == "Plain"
    assert source_json_schema(Plain) is None
    assert serialize_output_schema({"type": "json_object"}) == {"type": "json_object"}


def test_rehydrate_replaces_a_stored_response_format_and_keeps_it_for_saving():
    stored = json_schema_response_format(TICKET, name="Ticket", strict=True)
    config = {"output_schema": stored}
    rehydrate_inline_output_schema(config, strict=True, component_label="Agent 'a'")

    model = config["output_schema"]
    assert issubclass(model, BaseModel)
    assert serialize_output_schema(model) == stored


def test_rehydrate_leaves_provider_specific_dicts_alone():
    config = {"output_schema": {"type": "json_object"}}
    rehydrate_inline_output_schema(config, strict=True, component_label="Agent 'a'")
    assert config["output_schema"] == {"type": "json_object"}


def test_rehydrate_unsupported_schema_raises_when_strict_and_drops_it_otherwise():
    bad = json_schema_response_format({"type": "object", "properties": {"a": {"not": {}}}})
    with pytest.raises(ComponentRehydrationError, match="cannot be loaded"):
        rehydrate_inline_output_schema({"output_schema": bad}, strict=True, component_label="Agent 'a'")

    config = {"output_schema": bad}
    rehydrate_inline_output_schema(config, strict=False, component_label="Agent 'a'")
    assert "output_schema" not in config
