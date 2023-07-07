from typing import Optional

from pydantic import BaseModel, ConfigDict


class PhiBase(BaseModel):
    name: Optional[str] = None
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

    # -*- Waiter Control
    wait_for_create: bool = True
    wait_for_update: bool = True
    wait_for_delete: bool = True
    waiter_delay: int = 30
    waiter_max_attempts: int = 50

    #  -*- Save Resources to output directory
    # If True, output the resources to json files
    save_output: bool = False
    # The directory for the output files
    output_dir: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
