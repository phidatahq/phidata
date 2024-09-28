from uuid import uuid4
from typing import Any, Optional, Callable
from pydantic import BaseModel, ConfigDict, field_validator, Field, model_validator, PrivateAttr

from phi.utils.log import logger, set_log_level_to_debug


class Workflow(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = Field(None, validate_default=True)
    debug_mode: bool = False
    monitoring: bool = False

    _workflow_run: Optional[Callable] = PrivateAttr()
    _run_overridden: bool = PrivateAttr(default=False)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("id", mode="before")
    def set_id(cls, v: Optional[str]) -> str:
        return v if v is not None else str(uuid4())

    @field_validator("debug_mode", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    def run_wrapper(self, *args: Any, **kwargs: Any):
        logger.info(f"Starting run: {self.id}")
        if self._workflow_run is None:
            logger.error(f"run() not implemented for {self.__class__.__name__}")
            return
        self._workflow_run(*args, **kwargs)
        logger.info(f"Completed workflow: {self.id}")

    def run(self, *args: Any, **kwargs: Any):
        logger.warning(f"run() not implemented for {self.__class__.__name__}")

    @model_validator(mode="after")
    def update_run_function(self) -> "Workflow":
        if not self._run_overridden:
            logger.info("Updating run function")
            self._workflow_run = self.run
            object.__setattr__(self, "run", self.run_wrapper)
            self._run_overridden = True
        return self

    def workflow(self):
        logger.warning(f"workflow() not implemented for {self.__class__.__name__}")
