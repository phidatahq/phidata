from typing import Dict, List, Optional
from typing_extensions import Literal

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.resource.apiextensions_k8s_io.v1.custom_resource_definition import (
    CustomResourceDefinition,
    CustomResourceDefinitionSpec,
    CustomResourceDefinitionNames,
    CustomResourceDefinitionVersion,
    V1JSONSchemaProps,
)
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.cli_console import print_error
from phidata.utils.log import logger


class CreateCustomResourceDefinition(BaseModel):
    crd_name: str
    app_name: str
    group: str
    names: CustomResourceDefinitionNames
    scope: Literal["Cluster", "Namespaced"] = "Namespaced"
    versions: List[CustomResourceDefinitionVersion]
    annotations: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None

    def create(self) -> Optional[CustomResourceDefinition]:
        """Creates a CustomResourceDefinition resource"""

        crd_name = self.crd_name
        logger.debug(f"Init CRD resource: {crd_name}")

        crd_labels = create_component_labels_dict(
            component_name=crd_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        crd_versions: List[CustomResourceDefinitionVersion] = []
        if self.versions is not None and isinstance(self.versions, list):
            for version in self.versions:
                if isinstance(version, CustomResourceDefinitionVersion):
                    crd_versions.append(version)
        else:
            print_error("CustomResourceDefinitionVersion invalid")
            return None

        crd = CustomResourceDefinition(
            api_version=ApiVersion.APIEXTENSIONS_V1,
            kind=Kind.CUSTOMRESOURCEDEFINITION,
            metadata=ObjectMeta(
                name=crd_name,
                labels=crd_labels,
                annotations=self.annotations,
            ),
            spec=CustomResourceDefinitionSpec(
                group=self.group,
                names=self.names,
                scope=self.scope,
                versions=crd_versions,
            ),
        )

        # logger.debug(f"CRD {crd_name}:\n{crd.json(exclude_defaults=True, indent=2)}")
        return crd
