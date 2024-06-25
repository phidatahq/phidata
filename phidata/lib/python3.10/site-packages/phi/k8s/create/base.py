from phi.base import PhiBase
from phi.k8s.resource.base import K8sResource, K8sObject
from phi.utils.log import logger


class CreateK8sObject(PhiBase):
    def _create(self) -> K8sObject:
        raise NotImplementedError

    def create(self) -> K8sObject:
        _resource = self._create()
        if _resource is None:
            raise ValueError(f"Failed to create resource: {self.__class__.__name__}")

        resource_fields = _resource.model_dump(exclude_defaults=True)
        base_fields = self.model_dump(exclude_defaults=True)

        # Get fields that are set for the base class but not the resource class
        diff_fields = {k: v for k, v in base_fields.items() if k not in resource_fields}

        updated_resource = _resource.model_copy(update=diff_fields)
        # logger.debug(f"Created resource: {updated_resource.__class__.__name__}: {updated_resource.model_dump()}")

        return updated_resource


class CreateK8sResource(PhiBase):
    def _create(self) -> K8sResource:
        raise NotImplementedError

    def create(self) -> K8sResource:
        _resource = self._create()
        # logger.debug(f"Created resource: {self.__class__.__name__}")
        if _resource is None:
            raise ValueError(f"Failed to create resource: {self.__class__.__name__}")

        resource_fields = _resource.model_dump(exclude_defaults=True)
        base_fields = self.model_dump(exclude_defaults=True)

        # Get fields that are set for the base class but not the resource class
        diff_fields = {k: v for k, v in base_fields.items() if k not in resource_fields}

        updated_resource = _resource.model_copy(update=diff_fields)
        # logger.debug(f"Created resource: {updated_resource.__class__.__name__}: {updated_resource.model_dump()}")

        logger.debug(f"Created: {updated_resource.__class__.__name__} | {updated_resource.get_resource_name()}")
        return updated_resource
