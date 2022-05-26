from typing import Any, Dict, Optional

from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from pydantic import BaseModel, Field


class ObjectMeta(BaseModel):
    """
    ObjectMeta is metadata that all persisted resources must have,
    which includes all objects users must create.

    https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#objectmeta-v1-meta
    """

    resource_type: str = "ObjectMeta"

    # Name must be unique within a namespace. Is required when creating resources,
    # although some resources may allow a client to request the generation of an appropriate name automatically.
    # Name is primarily intended for creation idempotence and configuration definition.
    # Cannot be updated. More info: http://kubernetes.io/docs/user-guide/identifiers#names
    name: Optional[str] = None
    # Namespace defines the space within which each name must be unique.
    # An empty namespace is equivalent to the "default" namespace, but "default" is the canonical representation.
    # Not all objects are required to be scoped to a namespace -
    # the value of this field for those objects will be empty. Must be a DNS_LABEL.
    # Cannot be updated. More info: http://kubernetes.io/docs/user-guide/namespaces
    namespace: Optional[str] = None
    # Map of string keys and values that can be used to organize and categorize (scope and select) objects.
    # May match selectors of replication controllers and services.
    # More info: http://kubernetes.io/docs/user-guide/labels
    labels: Optional[Dict[str, str]] = None
    # Annotations is an unstructured key value map stored with a resource that may be set by external tools
    # to store and retrieve arbitrary metadata. They are not queryable and should be preserved when
    # modifying objects. More info: http://kubernetes.io/docs/user-guide/annotations
    annotations: Optional[Dict[str, str]] = None
    # The name of the cluster which the object belongs to. This is used to distinguish resources with same name
    # and namespace in different clusters. This field is not set anywhere right now and apiserver is going
    # to ignore it if set in create or update request.
    cluster_name: Optional[str] = Field(None, alias="clusterName")

    def get_k8s_object(self) -> V1ObjectMeta:
        # Return a V1ObjectMeta object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_object_meta.py
        _v1_object_meta = V1ObjectMeta(
            name=self.name,
            namespace=self.namespace,
            labels=self.labels,
            annotations=self.annotations,
            cluster_name=self.cluster_name,
        )
        return _v1_object_meta

    class Config:
        arbitrary_types_allowed = True
