from typing import Dict, List, Optional

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.enums.pv import PVAccessMode
from phidata.infra.k8s.resource.core.v1.persistent_volume_claim import (
    PersistentVolumeClaim,
    PersistentVolumeClaimSpec,
)
from phidata.infra.k8s.resource.core.v1.resource_requirements import (
    ResourceRequirements,
)
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.cli_console import print_info
from phidata.utils.log import logger


class CreatePVC(BaseModel):
    pvc_name: str
    app_name: str
    namespace: Optional[str] = None
    request_storage: str
    storage_class_name: str
    access_modes: List[PVAccessMode] = [PVAccessMode.READ_WRITE_ONCE]
    labels: Optional[Dict[str, str]] = None


def create_pvc_resource(data: CreatePVC) -> Optional[PersistentVolumeClaim]:
    """Creates a PersistentVolumeClaim resource."""

    if data is None:
        return None

    pvc_name = data.pvc_name
    logger.debug(f"Init PersistentVolumeClaim resource: {pvc_name}")

    pvc_labels = create_component_labels_dict(
        component_name=pvc_name,
        app_name=data.app_name,
        labels=data.labels,
    )

    pvc = PersistentVolumeClaim(
        api_version=ApiVersion.CORE_V1,
        kind=Kind.PERSISTENTVOLUMECLAIM,
        metadata=ObjectMeta(
            name=pvc_name,
            namespace=data.namespace,
            labels=pvc_labels,
        ),
        spec=PersistentVolumeClaimSpec(
            access_modes=data.access_modes,
            resources=ResourceRequirements(requests={"storage": data.request_storage}),
            storage_class_name=data.storage_class_name,
        ),
    )

    logger.info(
        f"PersistentVolumeClaim {pvc_name}:\n{pvc.json(exclude_defaults=True, indent=2)}"
    )
    return pvc
