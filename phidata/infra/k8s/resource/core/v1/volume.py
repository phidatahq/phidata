from typing import Optional

from kubernetes.client.models.v1_volume import V1Volume
from pydantic import Field

from phidata.infra.k8s.resource.base import K8sObject
from phidata.infra.k8s.resource.core.v1.volume_source import (
    AwsElasticBlockStoreVolumeSource,
    ConfigMapVolumeSource,
    EmptyDirVolumeSource,
    GcePersistentDiskVolumeSource,
    GitRepoVolumeSource,
    PersistentVolumeClaimVolumeSource,
    SecretVolumeSource,
    HostPathVolumeSource,
)


class Volume(K8sObject):
    """
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#volume-v1-core
    """

    resource_type: str = "Volume"

    # Volume's name. Must be a DNS_LABEL and unique within the pod.
    # More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    name: str

    ## Volume Sources
    aws_elastic_block_store: Optional[AwsElasticBlockStoreVolumeSource] = Field(
        None, alias="awsElasticBlockStore"
    )
    # ConfigMap represents a configMap that should populate this volume
    config_map: Optional[ConfigMapVolumeSource] = Field(None, alias="configMap")
    # EmptyDir represents a temporary directory that shares a pod's lifetime.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#emptydir
    empty_dir: Optional[EmptyDirVolumeSource] = Field(None, alias="emptyDir")
    # GCEPersistentDisk represents a GCE Disk resource that is attached to a
    # kubelet's host machine and then exposed to the pod. Provisioned by an admin.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#gcepersistentdisk
    gce_persistent_disk: Optional[GcePersistentDiskVolumeSource] = Field(
        None, alias="gcePersistentDisk"
    )
    # GitRepo represents a git repository at a particular revision.
    # DEPRECATED: GitRepo is deprecated.
    # To provision a container with a git repo, mount an EmptyDir into an InitContainer
    # that clones the repo using git, then mount the EmptyDir into the Pod's container.
    git_repo: Optional[GitRepoVolumeSource] = Field(None, alias="gitRepo")
    # HostPath represents a pre-existing file or directory on the host machine that is
    # directly exposed to the container. This is generally used for system agents or other privileged things
    # that are allowed to see the host machine. Most containers will NOT need this.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath
    host_path: Optional[HostPathVolumeSource] = Field(None, alias="hostPath")
    # PersistentVolumeClaimVolumeSource represents a reference to a PersistentVolumeClaim in the same namespace.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#persistentvolumeclaims
    persistent_volume_claim: Optional[PersistentVolumeClaimVolumeSource] = Field(
        None, alias="persistentVolumeClaim"
    )
    # Secret represents a secret that should populate this volume.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#secret
    secret: Optional[SecretVolumeSource] = None

    def get_k8s_object(self) -> V1Volume:
        # Return a V1Volume object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_volume.py
        _v1_volume = V1Volume(
            name=self.name,
            aws_elastic_block_store=self.aws_elastic_block_store.get_k8s_object()
            if self.aws_elastic_block_store
            else None,
            # azure_disk=None,
            # azure_file=None,
            # cephfs=None,
            # cinder=None,
            config_map=self.config_map.get_k8s_object() if self.config_map else None,
            # csi=None,
            # downward_api=None,
            empty_dir=self.empty_dir.get_k8s_object() if self.empty_dir else None,
            # ephemeral=None,
            # fc=None,
            # flex_volume=None,
            # flocker=None,
            gce_persistent_disk=self.gce_persistent_disk.get_k8s_object()
            if self.gce_persistent_disk
            else None,
            git_repo=self.git_repo.get_k8s_object() if self.git_repo else None,
            # glusterfs=None,
            host_path=self.host_path.get_k8s_object() if self.host_path else None,
            # iscsi=None,
            # nfs=None,
            persistent_volume_claim=self.persistent_volume_claim.get_k8s_object()
            if self.persistent_volume_claim
            else None,
            # photon_persistent_disk=None,
            # portworx_volume=None,
            # projected=None,
            # quobyte=None,
            # rbd=None,
            # scale_io=None,
            secret=self.secret.get_k8s_object() if self.secret else None,
            # storageos=None,
            # vsphere_volume=None,
        )
        return _v1_volume
