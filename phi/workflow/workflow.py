from uuid import uuid4
from typing import Any, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict, field_validator, PrivateAttr
from phi.utils.log import logger, set_log_level_to_debug


class Workflow(BaseModel):
    name: Optional[str] = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    debug_mode: bool = False
    monitoring: bool = False

    _original_run: Callable = PrivateAttr()
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_mode")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    def run(self, *args: Any, **kwargs: Any):
        logger.error(f"{self.__class__.__name__}.run() method not implemented.")
        return

    def run_wrapper(self, *args: Any, **kwargs: Any):
        logger.info(f"Starting workflow: {self.id}")
        result = self._original_run(*args, **kwargs)
        logger.info(f"Completed workflow: {self.id}")
        return result

    def __init__(self, **data):
        super().__init__(**data)
        # Check if 'run' is overridden in the subclass
        if self.__class__.run is not Workflow.run:
            # Store the original run method bound to the instance
            self._original_run = self.__class__.run.__get__(self)
            # Replace the instance's run method with run_wrapper
            object.__setattr__(self, "run", self.run_wrapper.__get__(self))
        else:
            # This will log an error when called
            self._original_run = self.run
