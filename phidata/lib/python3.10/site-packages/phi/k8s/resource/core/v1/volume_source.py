from typing import List, Optional, Union

from kubernetes.client.models.v1_aws_elastic_block_store_volume_source import (
    V1AWSElasticBlockStoreVolumeSource,
)
from kubernetes.client.models.v1_local_volume_source import V1LocalVolumeSource
from kubernetes.client.models.v1_nfs_volume_source import V1NFSVolumeSource
from kubernetes.client.models.v1_object_reference import V1ObjectReference
from kubernetes.client.models.v1_host_path_volume_source import V1HostPathVolumeSource
from kubernetes.client.models.v1_config_map_volume_source import V1ConfigMapVolumeSource
from kubernetes.client.models.v1_empty_dir_volume_source import V1EmptyDirVolumeSource
from kubernetes.client.models.v1_gce_persistent_disk_volume_source import (
    V1GCEPersistentDiskVolumeSource,
)
from kubernetes.client.models.v1_git_repo_volume_source import V1GitRepoVolumeSource
from kubernetes.client.models.v1_key_to_path import V1KeyToPath
from kubernetes.client.models.v1_persistent_volume_claim_volume_source import (
    V1PersistentVolumeClaimVolumeSource,
)
from kubernetes.client.models.v1_secret_volume_source import V1SecretVolumeSource
from pydantic import Field

from phi.k8s.resource.base import K8sObject


class KeyToPath(K8sObject):
    resource_type: str = "KeyToPath"

    key: str
    mode: int
    path: str


class AwsElasticBlockStoreVolumeSource(K8sObject):
    """
    Reference:
    - https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_aws_elastic_block_store_volume_source.py
    """

    resource_type: str = "AwsElasticBlockStoreVolumeSource"

    # Filesystem type of the volume that you want to mount.
    # Tip: Ensure that the filesystem type is supported by the host operating system.
    # Examples: "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#awselasticblockstore
    fs_type: Optional[str] = Field(None, alias="fsType")
    # The partition in the volume that you want to mount. If omitted, the default is to mount
    # by volume name. Examples: For volume /dev/sda1, you specify the partition as "1".
    # Similarly, the volume partition for /dev/sda is "0" (or you can leave the property empty).
    partition: Optional[int] = Field(None, alias="partition")
    # Specify "true" to force and set the ReadOnly property in VolumeMounts to "true".
    # If omitted, the default is "false".
    read_only: Optional[str] = Field(None, alias="readOnly")
    # Unique ID of the persistent disk resource in AWS (Amazon EBS volume).
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#awselasticblockstore
    volume_id: Optional[str] = Field(None, alias="volumeID")

    def get_k8s_object(
        self,
    ) -> V1AWSElasticBlockStoreVolumeSource:
        # Return a V1PersistentVolumeClaimVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_aws_elastic_block_store_volume_source.py
        _v1_aws_elastic_block_store_volume_source = V1AWSElasticBlockStoreVolumeSource(
            fs_type=self.fs_type,
            partition=self.partition,
            read_only=self.read_only,
            volume_id=self.volume_id,
        )
        return _v1_aws_elastic_block_store_volume_source


class LocalVolumeSource(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#localvolumesource-v1-core
    """

    resource_type: str = "LocalVolumeSource"

    # The full path to the volume on the node.
    # It can be either a directory or block device (disk, partition, ...).
    path: str
    # Filesystem type to mount. It applies only when the Path is a block device. Must be a filesystem type
    # supported by the host operating system. Ex. "ext4", "xfs", "ntfs".
    # The default value is to auto-select a filesystem if unspecified.
    fs_type: Optional[str] = Field(None, alias="fsType")

    def get_k8s_object(
        self,
    ) -> V1LocalVolumeSource:
        # Return a V1LocalVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_local_volume_source.py
        _v1_local_volume_source = V1LocalVolumeSource(
            fs_type=self.fs_type,
            path=self.path,
        )
        return _v1_local_volume_source


class HostPathVolumeSource(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#hostpathvolumesource-v1-core
    """

    resource_type: str = "HostPathVolumeSource"

    # Path of the directory on the host. If the path is a symlink, it will follow the link to the real path.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath
    path: str
    # Type for HostPath Volume Defaults to ""
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath
    type: Optional[str] = None

    def get_k8s_object(
        self,
    ) -> V1HostPathVolumeSource:
        # Return a V1HostPathVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_host_path_volume_source.py
        _v1_host_path_volume_source = V1HostPathVolumeSource(
            path=self.path,
            type=self.type,
        )
        return _v1_host_path_volume_source


class SecretVolumeSource(K8sObject):
    """
    Reference:
    - https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_secret_volume_source.py
    """

    resource_type: str = "SecretVolumeSource"

    secret_name: str = Field(..., alias="secretName")
    default_mode: Optional[int] = Field(None, alias="defaultMode")
    items: Optional[List[KeyToPath]] = None
    optional: Optional[bool] = None

    def get_k8s_object(self) -> V1SecretVolumeSource:
        # Return a V1SecretVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_secret_volume_source.py
        _items: Optional[List[V1KeyToPath]] = None
        if self.items:
            _items = []
            for _item in self.items:
                _items.append(
                    V1KeyToPath(
                        key=_item.key,
                        mode=_item.mode,
                        path=_item.path,
                    )
                )

        _v1_secret_volume_source = V1SecretVolumeSource(
            default_mode=self.default_mode,
            items=_items,
            secret_name=self.secret_name,
            optional=self.optional,
        )
        return _v1_secret_volume_source


class ConfigMapVolumeSource(K8sObject):
    """
    Reference:
    - https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_config_map_volume_source.py
    """

    resource_type: str = "ConfigMapVolumeSource"

    name: str
    default_mode: Optional[int] = Field(None, alias="defaultMode")
    items: Optional[List[KeyToPath]] = None
    optional: Optional[bool] = None

    def get_k8s_object(self) -> V1ConfigMapVolumeSource:
        # Return a V1ConfigMapVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_config_map_volume_source.py
        _items: Optional[List[V1KeyToPath]] = None
        if self.items:
            _items = []
            for _item in self.items:
                _items.append(
                    V1KeyToPath(
                        key=_item.key,
                        mode=_item.mode,
                        path=_item.path,
                    )
                )

        _v1_config_map_volume_source = V1ConfigMapVolumeSource(
            default_mode=self.default_mode,
            items=_items,
            name=self.name,
            optional=self.optional,
        )
        return _v1_config_map_volume_source


class EmptyDirVolumeSource(K8sObject):
    """
    Reference:
    - https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_empty_dir_volume_source.py
    """

    resource_type: str = "EmptyDirVolumeSource"

    medium: Optional[str] = None
    size_limit: Optional[str] = Field(None, alias="sizeLimit")

    def get_k8s_object(self) -> V1EmptyDirVolumeSource:
        # Return a V1EmptyDirVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_empty_dir_volume_source.py
        _v1_empty_dir_volume_source = V1EmptyDirVolumeSource(
            medium=self.medium,
            size_limit=self.size_limit,
        )
        return _v1_empty_dir_volume_source


class GcePersistentDiskVolumeSource(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#gcepersistentdiskvolumesource-v1-core
    """

    resource_type: str = "GcePersistentDiskVolumeSource"

    fs_type: str = Field(..., alias="fsType")
    partition: int
    pd_name: str
    read_only: Optional[bool] = Field(None, alias="readOnly")

    def get_k8s_object(
        self,
    ) -> V1GCEPersistentDiskVolumeSource:
        # Return a V1GCEPersistentDiskVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_gce_persistent_disk_volume_source.py
        _v1_gce_persistent_disk_volume_source = V1GCEPersistentDiskVolumeSource(
            fs_type=self.fs_type,
            partition=self.partition,
            pd_name=self.pd_name,
            read_only=self.read_only,
        )
        return _v1_gce_persistent_disk_volume_source


class GitRepoVolumeSource(K8sObject):
    """
    Reference:
    - https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_git_repo_volume_source.py
    """

    resource_type: str = "GitRepoVolumeSource"

    directory: str
    repository: str
    revision: str

    def get_k8s_object(self) -> V1GitRepoVolumeSource:
        # Return a V1GitRepoVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_git_repo_volume_source.py
        _v1_git_repo_volume_source = V1GitRepoVolumeSource(
            directory=self.directory,
            repository=self.repository,
            revision=self.revision,
        )
        return _v1_git_repo_volume_source


class PersistentVolumeClaimVolumeSource(K8sObject):
    """
    Reference:
    - https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_persistent_volume_claim_volume_source.py
    """

    resource_type: str = "PersistentVolumeClaimVolumeSource"

    claim_name: str = Field(..., alias="claimName")
    read_only: Optional[bool] = Field(None, alias="readOnly")

    def get_k8s_object(
        self,
    ) -> V1PersistentVolumeClaimVolumeSource:
        # Return a V1PersistentVolumeClaimVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_persistent_volume_claim_volume_source.py
        _v1_persistent_volume_claim_volume_source = V1PersistentVolumeClaimVolumeSource(
            claim_name=self.claim_name,
            read_only=self.read_only,
        )
        return _v1_persistent_volume_claim_volume_source


class NFSVolumeSource(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#nfsvolumesource-v1-core
    """

    resource_type: str = "NFSVolumeSource"

    # Path that is exported by the NFS server.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs
    path: str
    # ReadOnly here will force the NFS export to be mounted with read-only permissions.
    # Defaults to false. More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs
    read_only: Optional[bool] = Field(None, alias="readOnly")
    # Server is the hostname or IP address of the NFS server.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs
    server: Optional[str] = None

    def get_k8s_object(
        self,
    ) -> V1NFSVolumeSource:
        # Return a V1NFSVolumeSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_nfs_volume_source.py
        _v1_nfs_volume_source = V1NFSVolumeSource(path=self.path, read_only=self.read_only, server=self.server)
        return _v1_nfs_volume_source


class ClaimRef(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#persistentvolumespec-v1-core
    """

    resource_type: str = "ClaimRef"

    # Name of the referent.
    # More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    name: Optional[str] = None
    # Namespace of the referent.
    # More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/
    namespace: Optional[str] = None

    def get_k8s_object(
        self,
    ) -> V1ObjectReference:
        # Return a V1ObjectReference object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_object_reference.py
        _v1_object_reference = V1ObjectReference(
            name=self.name,
            namespace=self.namespace,
        )
        return _v1_object_reference


VolumeSourceType = Union[
    AwsElasticBlockStoreVolumeSource,
    ConfigMapVolumeSource,
    EmptyDirVolumeSource,
    GcePersistentDiskVolumeSource,
    GitRepoVolumeSource,
    PersistentVolumeClaimVolumeSource,
    SecretVolumeSource,
    NFSVolumeSource,
]
