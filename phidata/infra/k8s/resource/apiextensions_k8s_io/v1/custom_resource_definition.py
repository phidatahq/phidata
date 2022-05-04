from typing import List, Optional, Any, Dict
from typing_extensions import Literal

from kubernetes.client import ApiextensionsV1Api
from kubernetes.client.models.v1_custom_resource_definition import (
    V1CustomResourceDefinition,
)
from kubernetes.client.models.v1_custom_resource_definition_list import (
    V1CustomResourceDefinitionList,
)
from kubernetes.client.models.v1_custom_resource_definition_names import (
    V1CustomResourceDefinitionNames,
)
from kubernetes.client.models.v1_custom_resource_definition_spec import (
    V1CustomResourceDefinitionSpec,
)
from kubernetes.client.models.v1_custom_resource_definition_version import (
    V1CustomResourceDefinitionVersion,
)
from kubernetes.client.models.v1_custom_resource_validation import (
    V1CustomResourceValidation,
)
from kubernetes.client.models.v1_json_schema_props import V1JSONSchemaProps
from kubernetes.client.models.v1_status import V1Status
from pydantic import Field

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.base import K8sResource, K8sObject
from phidata.utils.cli_console import print_info
from phidata.utils.log import logger


class CustomResourceDefinitionNames(K8sObject):
    """
    # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_custom_resource_definition_names.py
    """

    resource_type: str = "CustomResourceDefinitionNames"

    # categories is a list of grouped resources this custom resource belongs to (e.g. 'all').
    # This is published in API discovery documents, and used by clients to support invocations like `kubectl get all`.
    categories: Optional[List[str]] = None
    # kind is the serialized kind of the resource. It is normally CamelCase and singular.
    # Custom resource instances will use this value as the `kind` attribute in API calls.
    kind: str
    # listKind is the serialized kind of the list for this resource.
    # Defaults to "`kind`List".
    list_kind: Optional[str] = Field(None, alias="listKind")
    # plural is the plural name of the resource to serve.
    # The custom resources are served under `/apis/<group>/<version>/.../<plural>`.
    # Must match the name of the CustomResourceDefinition (in the form `<names.plural>.<group>`).
    # Must be all lowercase.
    plural: Optional[str] = None
    # shortNames are short names for the resource, exposed in API discovery documents,
    # and used by clients to support invocations like `kubectl get <shortname>`.
    # It must be all lowercase.
    short_names: Optional[List[str]] = Field(None, alias="shortNames")
    # singular is the singular name of the resource. It must be all lowercase.
    # Defaults to lowercased `kind`.
    singular: Optional[str] = None

    def get_k8s_object(
        self,
    ) -> V1CustomResourceDefinitionNames:

        # Return a V1CustomResourceDefinitionNames object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_custom_resource_definition_names.py
        _v1_custom_resource_definition_names = V1CustomResourceDefinitionNames(
            categories=self.categories,
            kind=self.kind,
            list_kind=self.list_kind,
            plural=self.plural,
            short_names=self.short_names,
            singular=self.singular,
        )
        return _v1_custom_resource_definition_names


class CustomResourceDefinitionVersion(K8sObject):
    """
    # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_custom_resource_definition_version.py
    """

    resource_type: str = "CustomResourceDefinitionVersion"

    # name is the version name, e.g. “v1”, “v2beta1”, etc.
    # The custom resources are served under this version at `/apis/<group>/<version>/...` if `served` is true.
    name: str
    # served is a flag enabling/disabling this version from being served via REST APIs
    served: bool = True
    # storage indicates this version should be used when persisting custom resources to storage.
    # There must be exactly one version with storage=true.
    storage: bool = True
    # schema describes the schema used for validation, pruning, and defaulting of this version of the custom resource.
    # openAPIV3Schema is the OpenAPI v3 schema to use for validation and pruning.
    open_apiv3_schema: Optional[V1JSONSchemaProps] = Field(
        None, alias="openAPIV3Schema"
    )
    # deprecated indicates this version of the custom resource API is deprecated. When set to true,
    # API requests to this version receive a warning header in the server response. Defaults to false.
    deprecated: Optional[bool] = None
    # deprecationWarning overrides the default warning returned to API clients.
    # May only be set when `deprecated` is true. The default warning indicates this version is deprecated
    # and recommends use of the newest served version of equal or greater stability, if one exists.
    deprecation_warning: Optional[str] = Field(None, alias="openAPIV3Schema")

    def get_k8s_object(
        self,
    ) -> V1CustomResourceDefinitionVersion:

        # Return a V1CustomResourceDefinitionVersion object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_custom_resource_definition_version.py
        _v1_custom_resource_definition_version = V1CustomResourceDefinitionVersion(
            # additional_printer_columns=self.additional_printer_columns,
            deprecated=self.deprecated,
            deprecation_warning=self.deprecation_warning,
            name=self.name,
            schema=V1CustomResourceValidation(
                open_apiv3_schema=self.open_apiv3_schema,
            ),
            served=self.served,
            storage=self.storage,
            # subresources=self.subresources,
        )
        return _v1_custom_resource_definition_version


class CustomResourceDefinitionSpec(K8sObject):
    """
    # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_custom_resource_definition_spec.py
    """

    resource_type: str = "CustomResourceDefinitionSpec"

    group: str
    names: CustomResourceDefinitionNames
    preserve_unknown_fields: Optional[bool] = Field(None, alias="preserveUnknownFields")
    # scope indicates whether the defined custom resource is cluster- or namespace-scoped.
    # Allowed values are `Cluster` and `Namespaced`.
    scope: Literal["Cluster", "Namespaced"]
    # versions is the list of all API versions of the defined custom resource.
    # Version names are used to compute the order in which served versions are listed in API discovery.
    # If the version string is "kube-like", it will sort above non "kube-like" version strings,
    # which are ordered lexicographically. "Kube-like" versions start with a "v", then are followed by a number
    # (the major version), then optionally the string "alpha" or "beta" and another number
    # (the minor version). These are sorted first by GA > beta > alpha
    # (where GA is a version with no suffix such as beta or alpha),
    # and then by comparing major version, then minor version.
    # An example sorted list of versions: v10, v2, v1, v11beta2, v10beta3, v3beta1, v12alpha1, v11alpha2, foo1, foo10.
    versions: List[CustomResourceDefinitionVersion]

    def get_k8s_object(
        self,
    ) -> V1CustomResourceDefinitionSpec:

        # Return a V1CustomResourceDefinitionSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_custom_resource_definition_spec.py
        _v1_custom_resource_definition_spec = V1CustomResourceDefinitionSpec(
            group=self.group,
            names=self.names.get_k8s_object(),
            scope=self.scope,
            versions=[version.get_k8s_object() for version in self.versions],
        )
        return _v1_custom_resource_definition_spec


class CustomResourceDefinition(K8sResource):
    """
    References:
        * Doc: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#customresourcedefinition-v1-apiextensions-k8s-io
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_custom_resource_definition.py
    """

    resource_type: str = "CustomResourceDefinition"

    spec: CustomResourceDefinitionSpec

    # List of fields to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["spec"]

    def get_k8s_object(self) -> V1CustomResourceDefinition:
        """Creates a body for this CustomResourceDefinition"""

        # Return a V1CustomResourceDefinition object to create a CustomResourceDefinition
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_custom_resource_definition.py
        _v1_custom_resource_definition = V1CustomResourceDefinition(
            api_version=self.api_version,
            kind=self.kind,
            metadata=self.metadata.get_k8s_object(),
            spec=self.spec.get_k8s_object(),
        )
        return _v1_custom_resource_definition

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1CustomResourceDefinition]]:
        """Reads CustomResourceDefinitions from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        logger.debug(f"Getting CRDs from cluster")
        apiextensions_v1_api: ApiextensionsV1Api = k8s_client.apiextensions_v1_api
        crd_list: Optional[
            V1CustomResourceDefinitionList
        ] = apiextensions_v1_api.list_custom_resource_definition()
        crds: Optional[List[V1CustomResourceDefinition]] = None
        if crd_list:
            crds = crd_list.items
            # logger.debug(f"crds: {crds}")
            # logger.debug(f"crds type: {type(crds)}")
        return crds

    def _create(self, k8s_client: K8sApiClient) -> bool:

        apiextensions_v1_api: ApiextensionsV1Api = k8s_client.apiextensions_v1_api
        k8s_object: V1CustomResourceDefinition = self.get_k8s_object()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        try:
            v1_custom_resource_definition: V1CustomResourceDefinition = (
                apiextensions_v1_api.create_custom_resource_definition(
                    body=k8s_object,
                    async_req=self.async_req,
                    pretty=self.pretty,
                )
            )
            # logger.debug("Created: {}".format(v1_custom_resource_definition))
            if v1_custom_resource_definition.metadata.creation_timestamp is not None:
                logger.debug("CustomResourceDefinition Created")
                self.active_resource = v1_custom_resource_definition
                self.active_resource_class = V1CustomResourceDefinition
                return True
        except ValueError as e:
            # This is a K8s bug. Ref: https://github.com/kubernetes-client/python/issues/1022
            logger.warning("Encountered known K8s bug. Exception: {}".format(e))
        logger.error("CustomResourceDefinition could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1CustomResourceDefinition]:
        """Returns the "Active" CustomResourceDefinition from the cluster"""

        namespace = self.get_namespace()
        active_resource: Optional[V1CustomResourceDefinition] = None
        active_resources: Optional[
            List[V1CustomResourceDefinition]
        ] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_crd.metadata.name: _crd for _crd in active_resources}

        crd_name = self.get_resource_name()
        if crd_name in active_resources_dict:
            active_resource = active_resources_dict[crd_name]
            self.active_resource = active_resource
            self.active_resource_class = V1CustomResourceDefinition
            logger.debug(f"Found active {crd_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:

        apiextensions_v1_api: ApiextensionsV1Api = k8s_client.apiextensions_v1_api
        crd_name = self.get_resource_name()
        k8s_object: V1CustomResourceDefinition = self.get_k8s_object()

        logger.debug("Updating: {}".format(crd_name))
        v1_custom_resource_definition: V1CustomResourceDefinition = (
            apiextensions_v1_api.patch_custom_resource_definition(
                name=crd_name,
                body=k8s_object,
                async_req=self.async_req,
                pretty=self.pretty,
            )
        )
        # logger.debug("Updated: {}".format(v1_custom_resource_definition))
        if v1_custom_resource_definition.metadata.creation_timestamp is not None:
            logger.debug("CustomResourceDefinition Updated")
            self.active_resource = v1_custom_resource_definition
            self.active_resource_class = V1CustomResourceDefinition
            return True
        logger.error("CustomResourceDefinition could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        apiextensions_v1_api: ApiextensionsV1Api = k8s_client.apiextensions_v1_api
        crd_name = self.get_resource_name()

        logger.debug("Deleting: {}".format(crd_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = (
            apiextensions_v1_api.delete_custom_resource_definition(
                name=crd_name,
                async_req=self.async_req,
                pretty=self.pretty,
            )
        )
        # logger.debug("CRD delete_status type: {}".format(type(delete_status.status)))
        # logger.debug("CRD delete_status: {}".format(delete_status.status))
        # TODO: limit this if statement to when delete_status == Success
        if delete_status is not None:
            logger.debug("CustomResourceDefinition Deleted")
            return True
        return False

    def get_k8s_manifest_dict(self) -> Optional[Dict[str, Any]]:
        """Returns the K8s Manifest for a CRD as a dict
        Overwrite this function because the open_apiv3_schema cannot be
        converted to a dict

        Currently we return None meaning CRDs aren't processed by phi k commands
        TODO: fix this
        """
        return None
        # from itertools import chain
        #
        # k8s_manifest: Dict[str, Any] = {}
        # all_attributes: Dict[str, Any] = self.dict(exclude_defaults=True, by_alias=True)
        # # logger.debug("All Attributes: {}".format(all_attributes))
        # for attr_name in chain(
        #     self.fields_for_k8s_manifest_base, self.fields_for_k8s_manifest
        # ):
        #     if attr_name in all_attributes:
        #         if attr_name == "spec":
        #             continue
        #         else:
        #             k8s_manifest[attr_name] = all_attributes[attr_name]
        # # logger.debug(f"k8s_manifest:\n{k8s_manifest}")
        # return k8s_manifest
