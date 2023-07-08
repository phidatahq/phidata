from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict, field_validator

from phi.utils.log import logger


class PhiBase(BaseModel):
    name: Optional[str] = None
    group: Optional[str] = None
    version: Optional[str] = None
    enabled: bool = True

    #  -*- Resource Control
    skip_create: bool = False
    skip_read: bool = False
    skip_update: bool = False
    skip_delete: bool = False
    recreate_on_update: bool = False
    # Skip create if resource with the same name is active
    use_cache: bool = True
    # Force create/update/delete implementation
    force: bool = False

    # -*- Debug Mode
    debug_mode: bool = False

    # -*- Waiter Control
    wait_for_create: bool = True
    wait_for_update: bool = True
    wait_for_delete: bool = True
    waiter_delay: int = 30
    waiter_max_attempts: int = 50

    #  -*- Save to output directory
    # If True, save output to json files
    save_output: bool = False
    # The directory for the output files
    output_dir: Optional[str] = None

    #  -*- Dependencies
    depends_on: Optional[List[Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_group_name(self) -> Optional[str]:
        return self.group or self.name

    @field_validator("force", mode="before")
    def set_force(cls, force):
        logger.info(f"Setting force to {force}")
        from os import getenv

        force = force or getenv("PHI_WS_FORCE", False)
        return force
