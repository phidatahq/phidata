from phidata.utils.enums import ExtendedEnum


class K8sManagerStatus(ExtendedEnum):
    """Enum describing the current status of a K8sManager"""

    # Level 0: The K8sManager has just been created
    PRE_INIT = "PRE_INIT"

    # Level 1: Ready to deploy resources
    WORKER_READY = "WORKER_READY"

    # Level 2: Resources active
    RESOURCES_ACTIVE = "RESOURCES_ACTIVE"

    # Errors
    ERROR = "ERROR"

    def can_create_resources(self) -> bool:
        return self in (
            K8sManagerStatus.WORKER_READY,
            K8sManagerStatus.RESOURCES_ACTIVE,
        )

    def can_delete_resources(self) -> bool:
        return self in (
            K8sManagerStatus.WORKER_READY,
            K8sManagerStatus.RESOURCES_ACTIVE,
        )

    def can_get_resources(self) -> bool:
        return self in (
            K8sManagerStatus.WORKER_READY,
            K8sManagerStatus.RESOURCES_ACTIVE,
        )

    def can_read_resources(self) -> bool:
        return self in (
            K8sManagerStatus.WORKER_READY,
            K8sManagerStatus.RESOURCES_ACTIVE,
        )
