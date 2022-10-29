from typing import Dict, Optional

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.resource.core.v1.secret import Secret
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.log import logger


class CreateSecret(BaseModel):
    secret_name: str
    app_name: str
    secret_type: Optional[str] = "Opaque"
    namespace: Optional[str] = None
    data: Optional[Dict[str, str]] = None
    string_data: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None

    def create(self) -> Optional[Secret]:
        """Creates a Secret resource"""

        secret_name = self.secret_name
        logger.debug(f"Init Secret resource: {secret_name}")

        secret_labels = create_component_labels_dict(
            component_name=secret_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        secret = Secret(
            api_version=ApiVersion.CORE_V1,
            kind=Kind.SECRET,
            metadata=ObjectMeta(
                name=secret_name,
                namespace=self.namespace,
                labels=secret_labels,
            ),
            data=self.data,
            string_data=self.string_data,
            type=self.secret_type,
        )

        # logger.debug(
        #     f"Secret {secret_name}:\n{secret.json(exclude_defaults=True, indent=2)}"
        # )
        return secret
