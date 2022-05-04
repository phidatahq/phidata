from typing import Any, Optional, Type

from pydantic import BaseModel, validator

from phidata.utils.log import logger


class InfraResource(BaseModel):
    """Base class for all Phidata infrastructure resources.
    All Models in the phidata.infra.*.resource modules are expected to be subclasses of this Model.
    The rationale for using a pydantic model here is that the data which populates this
    model comes from an external infrastructure api, which can return anything so we need to
    validate the data were ingesting.
    """

    # type of resource
    resource_type: Optional[str] = None
    # name of resource
    name: Optional[str] = None

    # resource management
    # If True, skip resource creation if active resources with the same name exist.
    use_cache: bool = True
    # If True, logs extra debug messages
    use_verbose_logs: bool = False

    # If True, marks skip_create, skip_delete, skip_update to True
    external: bool = False
    # If True, does not create the resource when `phi ws up` command is run
    skip_create: bool = False
    # If True, does not delete the resource when `phi ws down` command is run
    skip_delete: bool = False
    # If True, does not update the resource when `phi ws patch` command is run
    skip_update: bool = False

    # If True, waits for the resource to be created
    wait_for_creation: bool = True
    # If True, waits for the resource to be deleted
    wait_for_deletion: bool = True
    # The amount of time in seconds to wait between attempts.
    waiter_delay: int = 30
    # The maximum number of attempts to be made.
    waiter_max_attempts: int = 50

    active_resource: Optional[Any] = None
    active_resource_class: Optional[Type] = None

    def get_resource_name(self) -> Optional[str]:
        return self.name

    def get_resource_type(self) -> Optional[str]:
        return self.resource_type

    def verbose_log(self, msg: Any) -> None:
        if self.use_verbose_logs:
            logger.debug(msg)

    @validator("skip_create", pre=True, always=True)
    def set_skip_create(cls, skip_create, values):
        external = values.get("external", False)
        return True if external else skip_create

    @validator("skip_delete", pre=True, always=True)
    def set_skip_delete(cls, skip_delete, values):
        external = values.get("external", False)
        return True if external else skip_delete

    @validator("skip_update", pre=True, always=True)
    def set_skip_update(cls, skip_update, values):
        external = values.get("external", False)
        return True if external else skip_update

    """
    ## Functions to be implemented by subclasses
    def create(self, infra_api_client: InfraApiClient) -> bool:
    def read(self, infra_api_client: InfraApiClient) -> bool:
    def update(self, infra_api_client: InfraApiClient) -> bool:
    def delete(self, infra_api_client: InfraApiClient) -> bool:
    def is_active(self, infra_api_client: InfraApiClient) -> bool:
    """

    class Config:
        # https://pydantic-docs.helpmanual.io/usage/model_config/
        # If we need to use an alias for fields of subclasses, eg: Kubeconfig
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        use_enum_values = True
