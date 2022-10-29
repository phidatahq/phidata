from typing import Dict, List, Optional

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.enums.storage_class import StorageClassType
from phidata.infra.k8s.resource.storage_k8s_io.v1.storage_class import StorageClass
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.infra.k8s.exceptions import StorageClassNotFoundException
from phidata.utils.cli_console import print_error
from phidata.utils.log import logger


class CreateStorageClass(BaseModel):
    storage_class_name: str
    app_name: str
    storage_class_type: Optional[StorageClassType] = None
    parameters: Optional[Dict[str, str]] = None
    provisioner: Optional[str] = None
    allow_volume_expansion: Optional[str] = None
    mount_options: Optional[List[str]] = None
    reclaim_policy: Optional[str] = None
    volume_binding_mode: Optional[str] = None
    namespace: Optional[str] = None
    labels: Optional[Dict[str, str]] = None

    def create(self) -> Optional[StorageClass]:
        """Creates a StorageClass resource."""

        logger.debug(f"Init StorageClass resource: {self.storage_class_name}")
        sc_labels = create_component_labels_dict(
            component_name=self.storage_class_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        # construct the provisioner and parameters
        sc_provisioner: str
        sc_parameters: Dict[str, str]

        # if the provisioner is provided, use that
        if self.provisioner is not None:
            sc_provisioner = self.provisioner
        # otherwise derive the provisioner from the StorageClassType
        elif self.storage_class_type is not None:
            if self.storage_class_type in (
                StorageClassType.GCE_SSD,
                StorageClassType.GCE_STANDARD,
            ):
                sc_provisioner = "kubernetes.io/gce-pd"
            else:
                raise StorageClassNotFoundException(
                    f"{self.storage_class_type} not found"
                )
        else:
            print_error(
                f"No provisioner or StorageClassType found for {self.storage_class_name}"
            )
            return None

        # if the parameters are provided use those
        if self.parameters is not None:
            sc_parameters = self.parameters
        # otherwise derive the parameters from the StorageClassType
        elif self.storage_class_type is not None:
            if self.storage_class_type == StorageClassType.GCE_SSD:
                sc_parameters = {"type": "pd-ssd"}
            if self.storage_class_type == StorageClassType.GCE_STANDARD:
                sc_parameters = {"type": "pd-standard"}
            else:
                raise StorageClassNotFoundException(
                    f"{self.storage_class_type} not found"
                )
        else:
            print_error(
                f"No parameters or StorageClassType found for {self.storage_class_name}"
            )
            return None

        _storage_class = StorageClass(
            api_version=ApiVersion.STORAGE_V1,
            kind=Kind.STORAGECLASS,
            metadata=ObjectMeta(
                name=self.storage_class_name,
                labels=sc_labels,
            ),
            allow_volume_expansion=self.allow_volume_expansion,
            mount_options=self.mount_options,
            provisioner=sc_provisioner,
            parameters=sc_parameters,
            reclaim_policy=self.reclaim_policy,
            volume_binding_mode=self.volume_binding_mode,
        )

        logger.debug(
            f"StorageClass {self.storage_class_name}:\n{_storage_class.json(exclude_defaults=True, indent=2)}"
        )
        return _storage_class
