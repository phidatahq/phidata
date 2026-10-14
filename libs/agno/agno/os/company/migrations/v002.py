"""Allocate short, immutable record keys without relying on process-local counters."""

SQL = """
CREATE SEQUENCE agno_company.record_keys;
INSERT INTO agno_company.schema_version(version) VALUES(2);
"""
