from phidata.utils.enums import ExtendedEnum


class DockerManagerStatus(ExtendedEnum):
    """Enum describing the current status of a DockerManager"""

    # Level 0: The DockerManager has just been created
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
            DockerManagerStatus.WORKER_READY,
            DockerManagerStatus.RESOURCES_INIT,
            DockerManagerStatus.RESOURCES_ACTIVE,
        )

    def can_delete_resources(self) -> bool:
        return self in (
            DockerManagerStatus.WORKER_READY,
            # DockerManagerStatus.RESOURCES_INIT,
            DockerManagerStatus.RESOURCES_ACTIVE,
        )

    def can_get_resources(self) -> bool:
        return self in (
            DockerManagerStatus.WORKER_READY,
            DockerManagerStatus.RESOURCES_INIT,
            DockerManagerStatus.RESOURCES_ACTIVE,
        )
