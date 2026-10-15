"""Framework-owned component IDs, reserved even when their feature is disabled."""

MANAGER_TEAM_ID = "os-manager-internal"
BUILDER_ID = "platform-builder-internal"
OPERATOR_ID = "platform-manager-internal"
RESERVED_MANAGER_IDS = frozenset({MANAGER_TEAM_ID, BUILDER_ID, OPERATOR_ID})
