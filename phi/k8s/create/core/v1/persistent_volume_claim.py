from typing import Dict, List, Optional

from phi.k8s.create.base import CreateK8sResource
from phi.k8s.enums.api_version import ApiVersion
from phi.k8s.enums.kind import Kind
from phi.k8s.enums.pv import PVAccessMode
from phi.k8s.resource.core.v1.persistent_volume_claim import (
    PersistentVolumeClaim,
    PersistentVolumeClaimSpec,
)
from phi.k8s.resource.core.v1.resource_requirements import (
    ResourceRequirements,
)
from phi.k8s.create.common.labels import create_component_labels_dict
from phi.k8s.resource.meta.v1.object_meta import ObjectMeta


class CreatePVC(CreateK8sResource):
    pvc_name: str
    app_name: str
    namespace: Optional[str] = None
    request_storage: str
    storage_class_name: str
    access_modes: List[PVAccessMode] = [PVAccessMode.READ_WRITE_ONCE]
    labels: Optional[Dict[str, str]] = None

    def _create(self) -> PersistentVolumeClaim:
        """Creates a PersistentVolumeClaim resource."""

        pvc_name = self.pvc_name
        # logger.debug(f"Init PersistentVolumeClaim resource: {pvc_name}")

        pvc_labels = create_component_labels_dict(
            component_name=pvc_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        pvc = PersistentVolumeClaim(
            name=pvc_name,
            api_version=ApiVersion.CORE_V1,
            kind=Kind.PERSISTENTVOLUMECLAIM,
            metadata=ObjectMeta(
                name=pvc_name,
                namespace=self.namespace,
                labels=pvc_labels,
            ),
            spec=PersistentVolumeClaimSpec(
                access_modes=self.access_modes,
                resources=ResourceRequirements(requests={"storage": self.request_storage}),
                storage_class_name=self.storage_class_name,
            ),
        )

        # logger.info(
        #     f"PersistentVolumeClaim {pvc_name}:\n{pvc.json(exclude_defaults=True, indent=2)}"
        # )
        return pvc
