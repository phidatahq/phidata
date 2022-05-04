from time import sleep
from typing import Any, Dict, List, Optional

from kubernetes.client import CustomObjectsApi
from kubernetes.client.models.v1_delete_options import V1DeleteOptions

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.base import K8sResource
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger


class CustomObject(K8sResource):
    """
    The CustomResourceDefinition must be created before creating this object.
    When creating a CustomObject, provide the spec and generate the object body using
        get_k8s_object()

    References:
        * https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/CustomObjectsApi.md
        * https://github.com/kubernetes-client/python/blob/master/examples/custom_object.py
    """

    resource_type: str = "CustomObject"

    # CustomObject spec
    spec: Optional[Dict[str, Any]] = None

    # The custom resource's group name (required)
    group: str
    # The custom resource's version (required)
    version: str
    # The custom resource's plural name. For TPRs this would be lowercase plural kind. (required)
    plural: str

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["spec"]

    def get_k8s_object(self) -> Dict[str, Any]:
        """Creates a body for this CustomObject"""

        _v1_custom_object = {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "metadata": self.metadata.get_k8s_object().to_dict(),
            "spec": self.spec,
        }
        return _v1_custom_object

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[Dict[str, Any]]]:
        """Reads CustomObject from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        if "group" not in kwargs:
            print_error("No Group provided when reading CustomObject")
            return None
        if "version" not in kwargs:
            print_error("No Version provided when reading CustomObject")
            return None
        if "plural" not in kwargs:
            print_error("No Plural provided when reading CustomObject")
            return None

        group = kwargs["group"]
        version = kwargs["version"]
        plural = kwargs["plural"]

        custom_objects_api: CustomObjectsApi = k8s_client.custom_objects_api
        custom_object_list: Optional[Dict[str, Any]] = None
        custom_objects: Optional[List[Dict[str, Any]]] = None
        try:
            if namespace:
                # logger.debug(
                #     f"Getting CustomObjects for:\n\tNS: {namespace}\n\tGroup: {group}\n\tVersion: {version}\n\tPlural: {plural}"
                # )
                custom_object_list = custom_objects_api.list_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural=plural,
                )
            else:
                # logger.debug(
                #     f"Getting CustomObjects for:\n\tGroup: {group}\n\tVersion: {version}\n\tPlural: {plural}"
                # )
                custom_object_list = custom_objects_api.list_cluster_custom_object(
                    group=group,
                    version=version,
                    plural=plural,
                )
        except Exception:
            logger.warning(f"Could not read custom objects for: {group}/{version}")
            logger.warning("Please check if the CustomResourceDefinition is created")
            return custom_objects

        # logger.debug(f"custom_object_list: {custom_object_list}")
        # logger.debug(f"custom_object_list type: {t    ype(custom_object_list)}")
        if custom_object_list:
            custom_objects = custom_object_list.get("items", None)
            # logger.debug(f"custom_objects: {custom_objects}")
            # logger.debug(f"custom_objects type: {type(custom_objects)}")
        return custom_objects

    def _create(self, k8s_client: K8sApiClient) -> bool:

        custom_objects_api: CustomObjectsApi = k8s_client.custom_objects_api
        k8s_object: Dict[str, Any] = self.get_k8s_object()
        namespace = self.get_namespace()

        print_info("Sleeping for 5 seconds so that CRDs can be registered")
        sleep(5)
        logger.debug("Creating: {}".format(self.get_resource_name()))
        custom_object: Dict[
            str, Any
        ] = custom_objects_api.create_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=namespace,
            plural=self.plural,
            body=k8s_object,
        )
        # logger.debug("Created:\n{}".format(pformat(custom_object, indent=2)))
        if custom_object.get("metadata", {}).get("creationTimestamp", None) is not None:
            logger.debug("CustomObject Created")
            self.active_resource = custom_object
            self.active_resource_class = Dict
            return True
        logger.error("CustomObject could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[Dict[str, Any]]:
        """Returns the "Active" CustomObject from the cluster"""

        namespace = self.get_namespace()
        active_resource: Optional[Dict[str, Any]] = None
        active_resources: Optional[List[Dict[str, Any]]] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
            group=self.group,
            version=self.version,
            plural=self.plural,
        )
        # logger.debug(f"active_resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {
            _custom_object.get("metadata", {}).get("name", None): _custom_object
            for _custom_object in active_resources
        }

        custom_object_name = self.get_resource_name()
        if custom_object_name in active_resources_dict:
            active_resource = active_resources_dict[custom_object_name]
            self.active_resource = active_resource
            self.active_resource_class = Dict
            logger.debug(f"Found active {custom_object_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:

        custom_objects_api: CustomObjectsApi = k8s_client.custom_objects_api
        custom_object_name = self.get_resource_name()
        k8s_object: Dict[str, Any] = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Updating: {}".format(custom_object_name))
        custom_object: Dict[
            str, Any
        ] = custom_objects_api.patch_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=namespace,
            plural=self.plural,
            name=custom_object_name,
            body=k8s_object,
        )
        # logger.debug("Updated: {}".format(custom_object))
        if custom_object.get("metadata", {}).get("creationTimestamp", None) is not None:
            logger.debug("CustomObject Updated")
            self.active_resource = custom_object
            self.active_resource_class = Dict
            return True
        logger.error("CustomObject could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        custom_objects_api: CustomObjectsApi = k8s_client.custom_objects_api
        custom_object_name = self.get_resource_name()
        namespace = self.get_namespace()

        logger.debug("Deleting: {}".format(custom_object_name))
        self.active_resource = None
        delete_options = V1DeleteOptions()
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: Dict[
            str, Any
        ] = custom_objects_api.delete_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=namespace,
            plural=self.plural,
            name=custom_object_name,
            body=delete_options,
        )
        logger.debug("delete_status: {}".format(delete_status))
        if delete_status.get("status", None) == "Success":
            logger.debug("CustomObject Deleted")
            return True
        logger.error("CustomObject could not be deleted")
        return False
