from typing import Optional, Dict, Any

from pydantic import BaseModel


class PhidataBaseArgs(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    enabled: bool = True

    #  -*- Resource Control
    skip_create: bool = False
    skip_read: bool = False
    skip_update: bool = False
    recreate_on_update: bool = False
    skip_delete: bool = False
    wait_for_creation: bool = True
    wait_for_update: bool = True
    wait_for_deletion: bool = True
    waiter_delay: int = 30
    waiter_max_attempts: int = 50

    #  -*- Save Resources to output directory
    # If True, save the resources to files
    save_output: bool = False
    # The resource directory for the output files
    resource_dir: Optional[str] = None

    # Skip creation if resource with the same name is active
    use_cache: bool = True

    class Config:
        arbitrary_types_allowed = True


class PhidataBase:
    """Phidata Base Class"""

    def __init__(self) -> None:
        self.args: PhidataBaseArgs = PhidataBaseArgs()

    @property
    def name(self) -> str:
        return self.args.name or self.__class__.__name__

    @property
    def version(self) -> Optional[str]:
        return self.args.version

    @property
    def enabled(self) -> bool:
        return self.args.enabled
