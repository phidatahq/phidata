from typing import Any, Optional, Type

from pydantic import BaseModel, validator


class InfraResource(BaseModel):
    """Base class for all Phidata infrastructure resources.
    All Models in the phidata.infra.*.resource modules are expected to be subclasses of this Model.

    We use a pydantic model for resources because the data which creates the resource
    may come from an external sources like users or an api.
    This data needs to be validated & type checked for which we use pydantic.
    """

    # name of resource
    name: Optional[str] = None
    # type of resource
    resource_type: Optional[str] = None

    # resource management
    # If True, skip resource creation if an active resources with the same name exists.
    use_cache: bool = True

    # If enabled=False: mark skip_create, skip_delete, skip_update as True
    enabled: bool = True
    # If True, phi does not create the resource
    skip_create: bool = False
    # If True, phi does not read the resource
    skip_read: bool = False
    # If True, phi does not update the resource
    skip_update: bool = False
    # If True, phi does not delete the resource
    skip_delete: bool = False

    # If True, waits for the resource to be created
    wait_for_creation: bool = True
    # If True, waits for the resource to be updated
    wait_for_update: bool = True
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

    @validator("skip_create", pre=True, always=True)
    def set_skip_create(cls, skip_create, values):
        skip_resource = not values.get("enabled", True)
        return True if skip_resource else skip_create

    @validator("skip_update", pre=True, always=True)
    def set_skip_update(cls, skip_update, values):
        skip_resource = not values.get("enabled", True)
        return True if skip_resource else skip_update

    @validator("skip_delete", pre=True, always=True)
    def set_skip_delete(cls, skip_delete, values):
        skip_resource = not values.get("enabled", True)
        return True if skip_resource else skip_delete

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
