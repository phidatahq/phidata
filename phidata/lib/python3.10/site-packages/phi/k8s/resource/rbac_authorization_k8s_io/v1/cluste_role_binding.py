from typing import List, Optional

from pydantic import Field, field_serializer

from kubernetes.client import RbacAuthorizationV1Api
from kubernetes.client.models.v1_cluster_role_binding import V1ClusterRoleBinding
from kubernetes.client.models.v1_cluster_role_binding_list import (
    V1ClusterRoleBindingList,
)
from kubernetes.client.models.v1_role_ref import V1RoleRef
from kubernetes.client.models.rbac_v1_subject import RbacV1Subject
from kubernetes.client.models.v1_status import V1Status

from phi.k8s.enums.api_group import ApiGroup
from phi.k8s.enums.kind import Kind
from phi.k8s.api_client import K8sApiClient
from phi.k8s.resource.base import K8sResource, K8sObject
from phi.utils.log import logger


class Subject(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#subject-v1-rbac-authorization-k8s-io
    """

    resource_type: str = "Subject"

    # Name of the object being referenced.
    name: str
    # Kind of object being referenced.
    # Values defined by this API group are "User", "Group", and "ServiceAccount".
    # If the Authorizer does not recognized the kind value, the Authorizer should report an error.
    kind: Kind
    # Namespace of the referenced object.
    # If the object kind is non-namespace, such as "User" or "Group", and this value is not empty
    # the Authorizer should report an error.
    namespace: Optional[str] = None
    # APIGroup holds the API group of the referenced subject.
    # Defaults to "" for ServiceAccount subjects.
    # Defaults to "rbac.authorization.k8s.io" for User and Group subjects.
    api_group: Optional[ApiGroup] = Field(None, alias="apiGroup")

    @field_serializer("api_group")
    def get_api_group_value(self, v) -> Optional[str]:
        return v.value if v else None

    @field_serializer("kind")
    def get_kind_value(self, v) -> str:
        return v.value

    def get_k8s_object(self) -> RbacV1Subject:
        # Return a RbacV1Subject object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/rbac_v1_subject.py
        _v1_subject = RbacV1Subject(
            api_group=self.api_group.value if self.api_group else None,
            kind=self.kind.value,
            name=self.name,
            namespace=self.namespace,
        )
        return _v1_subject


class RoleRef(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#roleref-v1-rbac-authorization-k8s-io
    """

    resource_type: str = "RoleRef"

    # APIGroup is the group for the resource being referenced
    api_group: ApiGroup = Field(..., alias="apiGroup")
    # Kind is the type of resource being referenced
    kind: Kind
    # Name is the name of resource being referenced
    name: str

    @field_serializer("api_group")
    def get_api_group_value(self, v) -> str:
        return v.value

    @field_serializer("kind")
    def get_kind_value(self, v) -> str:
        return v.value

    def get_k8s_object(self) -> V1RoleRef:
        # Return a V1RoleRef object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_role_ref.py
        _v1_role_ref = V1RoleRef(
            api_group=self.api_group.value,
            kind=self.kind.value,
            name=self.name,
        )
        return _v1_role_ref


class ClusterRoleBinding(K8sResource):
    """
    References:
    - Doc: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#clusterrolebinding-v1-rbac-authorization-k8s-io
    - Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_cluster_role_binding_binding.py
    """

    resource_type: str = "ClusterRoleBinding"

    role_ref: RoleRef = Field(..., alias="roleRef")
    subjects: List[Subject]

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["roleRef", "subjects"]

    # V1ClusterRoleBinding object received as the output after creating the crb
    v1_cluster_role_binding: Optional[V1ClusterRoleBinding] = None

    def get_k8s_object(self) -> V1ClusterRoleBinding:
        """Creates a body for this ClusterRoleBinding"""

        subjects_list = None
        if self.subjects:
            subjects_list = []
            for subject in self.subjects:
                subjects_list.append(subject.get_k8s_object())

        # Return a V1ClusterRoleBinding object to create a ClusterRoleBinding
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_cluster_role_binding.py
        _v1_cluster_role_binding = V1ClusterRoleBinding(
            api_version=self.api_version.value,
            kind=self.kind.value,
            metadata=self.metadata.get_k8s_object(),
            role_ref=self.role_ref.get_k8s_object(),
            subjects=subjects_list,
        )
        return _v1_cluster_role_binding

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1ClusterRoleBinding]]:
        """Reads ClusterRoles from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: NOT USED.
        """
        rbac_auth_v1_api: RbacAuthorizationV1Api = k8s_client.rbac_auth_v1_api
        crb_list: Optional[V1ClusterRoleBindingList] = rbac_auth_v1_api.list_cluster_role_binding()
        crbs: Optional[List[V1ClusterRoleBinding]] = None
        if crb_list:
            crbs = crb_list.items
            # logger.debug(f"crbs: {crbs}")
            # logger.debug(f"crbs type: {type(crbs)}")
        return crbs

    def _create(self, k8s_client: K8sApiClient) -> bool:
        rbac_auth_v1_api: RbacAuthorizationV1Api = k8s_client.rbac_auth_v1_api
        k8s_object: V1ClusterRoleBinding = self.get_k8s_object()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_cluster_role_binding: V1ClusterRoleBinding = rbac_auth_v1_api.create_cluster_role_binding(
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_cluster_role_binding))
        if v1_cluster_role_binding.metadata.creation_timestamp is not None:
            logger.debug("ClusterRoleBinding Created")
            self.active_resource = v1_cluster_role_binding
            return True
        logger.error("ClusterRoleBinding could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1ClusterRoleBinding]:
        """Returns the "Active" ClusterRoleBinding from the cluster"""

        active_resource: Optional[V1ClusterRoleBinding] = None
        active_resources: Optional[List[V1ClusterRoleBinding]] = self.get_from_cluster(
            k8s_client=k8s_client,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_crb.metadata.name: _crb for _crb in active_resources}

        crb_name = self.get_resource_name()
        if crb_name in active_resources_dict:
            active_resource = active_resources_dict[crb_name]
            self.active_resource = active_resource
            logger.debug(f"Found active {crb_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:
        rbac_auth_v1_api: RbacAuthorizationV1Api = k8s_client.rbac_auth_v1_api
        crb_name = self.get_resource_name()
        k8s_object: V1ClusterRoleBinding = self.get_k8s_object()

        logger.debug("Updating: {}".format(crb_name))
        v1_cluster_role_binding: V1ClusterRoleBinding = rbac_auth_v1_api.patch_cluster_role_binding(
            name=crb_name,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_cluster_role_binding.to_dict(), indent=2)))
        if v1_cluster_role_binding.metadata.creation_timestamp is not None:
            logger.debug("ClusterRoleBinding Updated")
            self.active_resource = v1_cluster_role_binding
            return True
        logger.error("ClusterRoleBinding could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:
        rbac_auth_v1_api: RbacAuthorizationV1Api = k8s_client.rbac_auth_v1_api
        crb_name = self.get_resource_name()

        logger.debug("Deleting: {}".format(crb_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = rbac_auth_v1_api.delete_cluster_role_binding(
            name=crb_name,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("ClusterRoleBinding Deleted")
            return True
        logger.error("ClusterRoleBinding could not be deleted")
        return False
