from typing import Optional, Any


class InfraApiClient:
    def __init__(self) -> None:
        self._api_client: Optional[Any] = None

    def is_initialized(self) -> bool:
        """
        Returns True if the ApiClient subclass is initialized properly.
        Needs to by implemented by each subclass
        """
        return False
