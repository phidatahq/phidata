from typing import List, Optional

from kubernetes.client import RbacAuthorizationV1Api
from kubernetes.client.models.v1_cluster_role import V1ClusterRole
from kubernetes.client.models.v1_cluster_role_list import V1ClusterRoleList
from kubernetes.client.models.v1_policy_rule import V1PolicyRule
from kubernetes.client.models.v1_status import V1Status
from pydantic import Field

from phi.k8s.api_client import K8sApiClient
from phi.k8s.resource.base import K8sResource, K8sObject
from phi.utils.log import logger


class PolicyRule(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#policyrule-v1-rbac-authorization-k8s-io
    """

    resource_type: str = "PolicyRule"

    api_groups: List[str] = Field(..., alias="apiGroups")
    resources: List[str]
    verbs: List[str]

    def get_k8s_object(self) -> V1PolicyRule:
        # Return a V1PolicyRule object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_policy_rule.py
        _v1_policy_rule = V1PolicyRule(
            api_groups=self.api_groups,
            resources=self.resources,
            verbs=self.verbs,
        )
        return _v1_policy_rule


class ClusterRole(K8sResource):
    """
    References:
    - Doc: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#clusterrole-v1-rbac-authorization-k8s-io
    - Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_cluster_role.py
    """

    resource_type: str = "ClusterRole"

    # Rules holds all the PolicyRules for this ClusterRole
    rules: List[PolicyRule]

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["rules"]

    def get_k8s_object(self) -> V1ClusterRole:
        """Creates a body for this ClusterRole"""

        rules_list = None
        if self.rules:
            rules_list = []
            for rules in self.rules:
                rules_list.append(rules.get_k8s_object())

        # Return a V1ClusterRole object to create a ClusterRole
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_cluster_role.py
        _v1_cluster_role = V1ClusterRole(
            api_version=self.api_version.value,
            kind=self.kind.value,
            metadata=self.metadata.get_k8s_object(),
            rules=rules_list,
        )

        return _v1_cluster_role

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1ClusterRole]]:
        """Reads ClusterRoles from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: NOT USED.
        """
        rbac_auth_v1_api: RbacAuthorizationV1Api = k8s_client.rbac_auth_v1_api
        cr_list: Optional[V1ClusterRoleList] = rbac_auth_v1_api.list_cluster_role(**kwargs)
        crs: Optional[List[V1ClusterRole]] = None
        if cr_list:
            crs = cr_list.items
            # logger.debug(f"crs: {crs}")
            # logger.debug(f"crs type: {type(crs)}")
        return crs

    def _create(self, k8s_client: K8sApiClient) -> bool:
        rbac_auth_v1_api: RbacAuthorizationV1Api = k8s_client.rbac_auth_v1_api
        k8s_object: V1ClusterRole = self.get_k8s_object()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_cluster_role: V1ClusterRole = rbac_auth_v1_api.create_cluster_role(
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_cluster_role))
        if v1_cluster_role.metadata.creation_timestamp is not None:
            logger.debug("ClusterRole Created")
            self.active_resource = v1_cluster_role
            return True
        logger.error("ClusterRole could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1ClusterRole]:
        """Returns the "Active" ClusterRole from the cluster"""

        active_resource: Optional[V1ClusterRole] = None
        active_resources: Optional[List[V1ClusterRole]] = self.get_from_cluster(
            k8s_client=k8s_client,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_cr.metadata.name: _cr for _cr in active_resources}

        cr_name = self.get_resource_name()
        if cr_name in active_resources_dict:
            active_resource = active_resources_dict[cr_name]
            self.active_resource = active_resource
            logger.debug(f"Found active {cr_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:
        rbac_auth_v1_api: RbacAuthorizationV1Api = k8s_client.rbac_auth_v1_api
        cr_name = self.get_resource_name()
        k8s_object: V1ClusterRole = self.get_k8s_object()

        logger.debug("Updating: {}".format(cr_name))
        v1_cluster_role: V1ClusterRole = rbac_auth_v1_api.patch_cluster_role(
            name=cr_name,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_cluster_role.to_dict(), indent=2)))
        if v1_cluster_role.metadata.creation_timestamp is not None:
            logger.debug("ClusterRole Updated")
            self.active_resource = v1_cluster_role
            return True
        logger.error("ClusterRole could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:
        rbac_auth_v1_api: RbacAuthorizationV1Api = k8s_client.rbac_auth_v1_api
        cr_name = self.get_resource_name()

        logger.debug("Deleting: {}".format(cr_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = rbac_auth_v1_api.delete_cluster_role(
            name=cr_name,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("ClusterRole Deleted")
            return True
        logger.error("ClusterRole could not be deleted")
        return False
