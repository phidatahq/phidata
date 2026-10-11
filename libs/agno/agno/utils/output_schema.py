"""Local JSON Schema validation for harness output contracts."""

from typing import Any, Dict


def output_validator(schema: Dict[str, Any]) -> Any:
    """Build a validator without fetching references from the network."""
    from jsonschema.validators import validator_for  # type: ignore[import-untyped]
    from referencing import Registry, Resource
    from referencing.exceptions import Unresolvable
    from referencing.jsonschema import DRAFT202012

    validator = validator_for(schema)
    validator.check_schema(schema)
    # Walk schema resources, not arbitrary JSON values: a literal object in an
    # enum may contain a "$ref" property without referencing another schema.
    root = Resource.from_contents(schema, default_specification=DRAFT202012)
    pending = [(root, Registry().resolver_with_root(root))]
    while pending:
        resource, resolver = pending.pop()
        value = resource.contents
        if isinstance(value, dict):
            for keyword in ("$ref", "$dynamicRef", "$recursiveRef"):
                reference = value.get(keyword)
                if isinstance(reference, str) and not reference.startswith("#"):
                    raise ValueError("output_schema references must be local to the schema")
                if isinstance(reference, str):
                    try:
                        resolver.lookup(reference)
                    except Unresolvable as exc:
                        raise ValueError("output_schema contains an unresolved local reference") from exc
        pending.extend((child, resolver.in_subresource(child)) for child in resource.subresources())
    # An empty registry refuses missing references rather than retrieving URLs.
    return validator(schema, registry=Registry())
