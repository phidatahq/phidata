from typing import Dict, List, Optional

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.resource.core.v1.service_account import (
    ServiceAccount,
    LocalObjectReference,
    ObjectReference,
)
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.common import get_default_sa_name
from phidata.utils.log import logger


class CreateServiceAccount(BaseModel):
    sa_name: str
    app_name: str
    automount_service_account_token: Optional[bool] = None
    image_pull_secrets: Optional[List[str]] = None
    secrets: Optional[List[ObjectReference]] = None
    namespace: Optional[str] = None
    labels: Optional[Dict[str, str]] = None

    def create(self) -> Optional[ServiceAccount]:

        sa_name = self.sa_name if self.sa_name else get_default_sa_name(self.app_name)
        logger.debug(f"Init ServiceAccount resource: {sa_name}")

        sa_labels = create_component_labels_dict(
            component_name=sa_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        sa_image_pull_secrets: Optional[List[LocalObjectReference]] = None
        if self.image_pull_secrets is not None and isinstance(
            self.image_pull_secrets, list
        ):
            sa_image_pull_secrets = []
            for _ips in self.image_pull_secrets:
                sa_image_pull_secrets.append(LocalObjectReference(name=_ips))

        sa = ServiceAccount(
            api_version=ApiVersion.CORE_V1,
            kind=Kind.SERVICEACCOUNT,
            metadata=ObjectMeta(
                name=sa_name,
                namespace=self.namespace,
                labels=sa_labels,
            ),
            automount_service_account_token=self.automount_service_account_token,
            image_pull_secrets=sa_image_pull_secrets,
            secrets=self.secrets,
        )
        return sa
