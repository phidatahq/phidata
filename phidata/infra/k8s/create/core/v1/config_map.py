from typing import Any, Dict, Optional

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.resource.core.v1.config_map import ConfigMap
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.log import logger


class CreateConfigMap(BaseModel):
    cm_name: str
    app_name: str
    namespace: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, str]] = None

    def create(self) -> Optional[ConfigMap]:
        """Creates the ConfigMap resource"""

        cm_name = self.cm_name
        logger.debug(f"Init ConfigMap resource: {cm_name}")

        cm_labels = create_component_labels_dict(
            component_name=cm_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        configmap = ConfigMap(
            api_version=ApiVersion.CORE_V1,
            kind=Kind.CONFIGMAP,
            metadata=ObjectMeta(
                name=cm_name,
                namespace=self.namespace,
                labels=cm_labels,
            ),
            data=self.data,
        )

        # logger.debug(
        #     f"ConfigMap {cm_name}:\n{configmap.json(exclude_defaults=True, indent=2)}"
        # )
        return configmap
