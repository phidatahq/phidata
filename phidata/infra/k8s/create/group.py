from typing import Dict, List, Optional, Type

from pydantic import BaseModel

from phidata.infra.k8s.create.apps.v1.deployment import CreateDeployment
from phidata.infra.k8s.create.core.v1.config_map import CreateConfigMap
from phidata.infra.k8s.create.core.v1.namespace import CreateNamespace
from phidata.infra.k8s.create.core.v1.secret import CreateSecret
from phidata.infra.k8s.create.core.v1.service import CreateService
from phidata.infra.k8s.create.core.v1.service_account import CreateServiceAccount
from phidata.infra.k8s.create.apiextensions_k8s_io.v1.custom_resource_definition import (
    CreateCustomResourceDefinition,
)
from phidata.infra.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import (
    CreateClusterRole,
)
from phidata.infra.k8s.create.rbac_authorization_k8s_io.v1.cluste_role_binding import (
    CreateClusterRoleBinding,
)
from phidata.infra.k8s.create.apiextensions_k8s_io.v1.custom_object import (
    CreateCustomObject,
)
from phidata.infra.k8s.create.storage_k8s_io.v1.storage_class import CreateStorageClass
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.cli_console import print_error
from phidata.utils.log import logger


class CreateK8sResourceGroup(BaseModel):
    name: str
    enabled: bool = True
    weight: int = 100
    ns: Optional[CreateNamespace] = None
    sa: Optional[CreateServiceAccount] = None
    cr: Optional[CreateClusterRole] = None
    crb: Optional[CreateClusterRoleBinding] = None
    secrets: Optional[List[CreateSecret]] = None
    config_maps: Optional[List[CreateConfigMap]] = None
    storage_classes: Optional[List[CreateStorageClass]] = None
    services: Optional[List[CreateService]] = None
    deployments: Optional[List[CreateDeployment]] = None
    custom_objects: Optional[List[CreateCustomObject]] = None
    crds: Optional[List[CreateCustomResourceDefinition]] = None

    def create(self) -> Optional[K8sResourceGroup]:
        """Creates the K8sResourceGroup"""

        # logger.debug(f"Creating K8sResourceGroup: {self.name}")
        k8s_resource_group: K8sResourceGroup = K8sResourceGroup(
            name=self.name,
            enabled=self.enabled,
            weight=self.weight,
        )

        for key, value in self.__dict__.items():

            if value is None:
                continue
            # logger.debug(f"Parsing {key}")

            ######################################################
            ## Create Namespace
            ######################################################
            elif key == "ns":
                from phidata.infra.k8s.resource.core.v1.namespace import Namespace

                if not isinstance(value, CreateNamespace):
                    logger.error(
                        f"Expected: CreateNamespace. Received: {type(value)}. Skipping."
                    )
                    continue

                _ns_resource: Optional[Namespace] = value.create()
                if _ns_resource is not None:
                    k8s_resource_group.ns = _ns_resource

            ######################################################
            ## Create ServiceAccount
            ######################################################
            elif key == "sa":
                from phidata.infra.k8s.resource.core.v1.service_account import (
                    ServiceAccount,
                )

                if not isinstance(value, CreateServiceAccount):
                    logger.error(
                        f"Expected: CreateServiceAccount. Received: {type(value)}. Skipping."
                    )
                    continue

                _sa_resource: Optional[ServiceAccount] = value.create()
                if _sa_resource is not None:
                    k8s_resource_group.sa = _sa_resource

            ######################################################
            ## Create ClusterRole
            ######################################################
            elif key == "cr":
                from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluster_role import (
                    ClusterRole,
                )

                if not isinstance(value, CreateClusterRole):
                    logger.error(
                        f"Expected: CreateClusterRole. Received: {type(value)}. Skipping."
                    )
                    continue

                _cr_resource: Optional[ClusterRole] = value.create()
                if _cr_resource is not None:
                    k8s_resource_group.cr = _cr_resource

            ######################################################
            ## Create ClusterRoleBinding
            ######################################################
            elif key == "crb":
                from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluste_role_binding import (
                    ClusterRoleBinding,
                )

                if not isinstance(value, CreateClusterRoleBinding):
                    logger.error(
                        f"Expected: CreateClusterRoleBinding. Received: {type(value)}. Skipping."
                    )
                    continue

                _crb_resource: Optional[ClusterRoleBinding] = value.create()
                if _crb_resource is not None:
                    k8s_resource_group.crb = _crb_resource

            ######################################################
            ## Create Secrets
            ######################################################
            elif key == "secrets":
                if not isinstance(value, List):
                    logger.error(
                        f"Expected: List[CreateSecret]. Received: {type(value)}. Skipping."
                    )
                    continue

                from phidata.infra.k8s.resource.core.v1.secret import Secret

                secret_resources: List[Secret] = []
                for _secret in value:
                    if not isinstance(_secret, CreateSecret):
                        logger.error(
                            f"Expected: CreateSecret. Received: {type(_secret)}. Skipping."
                        )
                        continue
                    _secret_resource: Optional[Secret] = _secret.create()
                    if _secret_resource is not None:
                        secret_resources.append(_secret_resource)
                if len(secret_resources) >= 0:
                    k8s_resource_group.secrets = secret_resources

            ######################################################
            ## Create ConfigMaps
            ######################################################
            elif key == "config_maps":
                if not isinstance(value, List):
                    logger.error(
                        f"Expected: List[CreateConfigMap]. Received: {type(value)}. Skipping."
                    )
                    continue

                from phidata.infra.k8s.resource.core.v1.config_map import ConfigMap

                cm_resources: List[ConfigMap] = []
                for _config_map in value:
                    if not isinstance(_config_map, CreateConfigMap):
                        logger.error(
                            f"Expected: CreateConfigMap. Received: {type(_config_map)}. Skipping."
                        )
                        continue
                    _cm_resource: Optional[ConfigMap] = _config_map.create()
                    if _cm_resource is not None:
                        cm_resources.append(_cm_resource)
                if len(cm_resources) >= 0:
                    k8s_resource_group.config_maps = cm_resources

            ######################################################
            ## Create StorageClasses
            ######################################################
            elif key == "storage_classes":
                if not isinstance(value, List):
                    logger.error(
                        f"Expected: List[CreateStorageClass]. Received: {type(value)}. Skipping."
                    )
                    continue

                from phidata.infra.k8s.resource.storage_k8s_io.v1.storage_class import (
                    StorageClass,
                )

                sc_resources: List[StorageClass] = []
                for _storage_class in value:
                    if not isinstance(_storage_class, CreateStorageClass):
                        logger.error(
                            f"Expected: CreateStorageClass. Received: {type(_storage_class)}. Skipping."
                        )
                        continue
                    _sc_resource: Optional[StorageClass] = _storage_class.create()
                    if _sc_resource is not None:
                        sc_resources.append(_sc_resource)
                if len(sc_resources) >= 0:
                    k8s_resource_group.storage_classes = sc_resources

            ######################################################
            ## Create Services
            ######################################################
            if key == "services":
                if not isinstance(value, List):
                    logger.error(
                        f"Expected: List[CreateService]. Received: {type(value)}. Skipping."
                    )
                    continue

                # Add necessary imports here to speed up file load time
                from phidata.infra.k8s.resource.core.v1.service import Service

                service_resources: List[Service] = []
                for _service in value:
                    if not isinstance(_service, CreateService):
                        logger.error(
                            f"Expected: CreateService. Received: {type(_service)}. Skipping."
                        )
                        continue
                    _service_resource: Optional[Service] = _service.create()
                    if _service_resource is not None:
                        service_resources.append(_service_resource)
                if len(service_resources) >= 0:
                    k8s_resource_group.services = service_resources

            ######################################################
            ## Create Deployments
            ######################################################
            if key == "deployments":
                if not isinstance(value, List):
                    logger.error(
                        f"Expected: List[CreateDeployment]. Received: {type(value)}. Skipping."
                    )
                    continue

                # Add necessary imports here to speed up file load time
                from phidata.infra.k8s.resource.apps.v1.deployment import Deployment

                deploy_resources: List[Deployment] = []
                for _deployment in value:
                    if not isinstance(_deployment, CreateDeployment):
                        logger.error(
                            f"Expected: CreateDeployment. Received: {type(_deployment)}. Skipping."
                        )
                        continue
                    _deployment_resource: Optional[Deployment] = _deployment.create()
                    if _deployment_resource is not None:
                        deploy_resources.append(_deployment_resource)
                # logger.debug(deploy_resources)
                if len(deploy_resources) >= 0:
                    k8s_resource_group.deployments = deploy_resources

            ######################################################
            ## Create CustomResourceDefinitions
            ######################################################
            if key == "custom_objects":
                if not isinstance(value, List):
                    logger.error(
                        f"Expected: List[CreateCustomObject]. Received: {type(value)}. Skipping."
                    )
                    continue

                # Add necessary imports here to speed up file load time
                from phidata.infra.k8s.resource.apiextensions_k8s_io.v1.custom_object import (
                    CustomObject,
                )

                custom_object_resources: List[CustomObject] = []
                for _custom_object in value:
                    if not isinstance(_custom_object, CreateCustomObject):
                        logger.error(
                            f"Expected: CreateCustomObject. Received: {type(_custom_object)}. Skipping."
                        )
                        continue
                    _custom_object_resource: Optional[
                        CustomObject
                    ] = _custom_object.create()
                    if _custom_object_resource is not None:
                        custom_object_resources.append(_custom_object_resource)
                if len(custom_object_resources) >= 0:
                    k8s_resource_group.custom_objects = custom_object_resources

            ######################################################
            ## Create CustomResourceDefinitions
            ######################################################
            if key == "crds":
                if not isinstance(value, List):
                    logger.error(
                        f"Expected: List[CreateCustomResourceDefinition]. Received: {type(value)}. Skipping."
                    )
                    continue

                # Add necessary imports here to speed up file load time
                from phidata.infra.k8s.resource.apiextensions_k8s_io.v1.custom_resource_definition import (
                    CustomResourceDefinition,
                )

                crd_resources: List[CustomResourceDefinition] = []
                for _crd in value:
                    if not isinstance(_crd, CreateCustomResourceDefinition):
                        logger.error(
                            f"Expected: CreateCustomResourceDefinition. Received: {type(_crd)}. Skipping."
                        )
                        continue
                    _crd_resource: Optional[CustomResourceDefinition] = _crd.create()
                    if _crd_resource is not None:
                        crd_resources.append(_crd_resource)
                if len(crd_resources) >= 0:
                    k8s_resource_group.crds = crd_resources

        logger.debug(f"-*- Initialized K8sResourceGroup for: {self.name}")
        return k8s_resource_group
