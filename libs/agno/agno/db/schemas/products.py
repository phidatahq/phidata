"""Validation shared by Product managers and database adapters."""

from typing import Any, Dict


def validate_product_fields(fields: Dict[str, Any]) -> None:
    """Accept only descriptive edits; identity and lifecycle use dedicated methods."""
    unknown = set(fields) - {"name", "purpose", "metadata"}
    if unknown:
        raise ValueError(f"Unsupported product fields: {sorted(unknown)}")
    if "name" in fields and (not isinstance(fields["name"], str) or not fields["name"].strip()):
        raise ValueError("name must be a non-empty string")
    if fields.get("purpose") is not None and not isinstance(fields["purpose"], str):
        raise ValueError("purpose must be a string or None")
    if fields.get("metadata") is not None and not isinstance(fields["metadata"], dict):
        raise ValueError("metadata must be a dictionary or None")
