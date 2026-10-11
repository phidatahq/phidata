"""Local JSON Schema validation for harness output contracts."""

from typing import Any, Dict


def output_validator(schema: Dict[str, Any]) -> Any:
    """Build a validator without fetching references from the network."""
    from jsonschema.validators import validator_for  # type: ignore[import-untyped]
    from referencing import Registry

    # Output contracts must be self-contained. A caller-supplied reference must
    # never turn answer validation into a network request or filesystem read.
    def check_refs(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and not reference.startswith("#"):
                raise ValueError("output_schema references must be local to the schema")
            for item in value.values():
                check_refs(item)
        elif isinstance(value, list):
            for item in value:
                check_refs(item)

    check_refs(schema)
    validator = validator_for(schema)
    validator.check_schema(schema)
    return validator(schema, registry=Registry())
