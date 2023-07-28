from typing import Optional

from phi.k8s.resource.base import K8sResource
from phi.utils.log import logger


class CreateResourceBase(K8sResource):
    def _get_resource(self) -> Optional[K8sResource]:
        raise NotImplementedError

    def get_resource(self) -> Optional[K8sResource]:
        _resource = self._get_resource()
        if _resource is None:
            return None

        resource_fields = _resource.model_dump(exclude_defaults=True)
        base_fields = self.model_dump(exclude_defaults=True)

        # Get fields that are set for the base class but not the resource class
        diff_fields = {k: v for k, v in base_fields.items() if k not in resource_fields}

        updated_resource = _resource.model_copy(update=diff_fields)
        logger.debug(f"Created resource: {updated_resource.__class__.__name__}: {updated_resource.model_dump()}")

        return updated_resource
