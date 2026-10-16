"""Framework-owned component IDs, reserved even when their feature is disabled."""

MANAGER_TEAM_ID = "os-manager-internal"
BUILDER_ID = "platform-builder-internal"
OPERATOR_ID = "platform-manager-internal"
PRODUCT_MANAGER_ID = "product-manager-internal"
RESERVED_MEMBER_IDS = frozenset({BUILDER_ID, OPERATOR_ID})
RESERVED_MANAGER_IDS = RESERVED_MEMBER_IDS | {MANAGER_TEAM_ID, PRODUCT_MANAGER_ID}


def _reserved_manager_id_message(component_id: str) -> str:
    return f"Component ID '{component_id}' is reserved. Please choose a different ID for your component."
