from phidata.utils.enums import ExtendedEnum


class AwsManagerStatus(ExtendedEnum):
    """Enum describing the current status of a AwsManager"""

    # Level 0: The AwsManager has just been created
    PRE_INIT = "PRE_INIT"

    # Level 1: Ready to deploy resources
    WORKER_READY = "WORKER_READY"

    # Level 2: Resources initialized
    RESOURCES_INIT = "RESOURCES_INIT"

    # Level 3: Resources active
    RESOURCES_ACTIVE = "RESOURCES_ACTIVE"

    # Errors
    ERROR = "ERROR"

    def can_create_resources(self) -> bool:
        return self in (
            AwsManagerStatus.WORKER_READY,
            AwsManagerStatus.RESOURCES_INIT,
            AwsManagerStatus.RESOURCES_ACTIVE,
        )

    def can_delete_resources(self) -> bool:
        return self in (
            AwsManagerStatus.WORKER_READY,
            AwsManagerStatus.RESOURCES_ACTIVE,
        )

    def can_get_resources(self) -> bool:
        return self in (
            AwsManagerStatus.WORKER_READY,
            AwsManagerStatus.RESOURCES_INIT,
            AwsManagerStatus.RESOURCES_ACTIVE,
        )
