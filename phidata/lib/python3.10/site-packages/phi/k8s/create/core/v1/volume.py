from typing import Optional

from phi.k8s.create.base import CreateK8sObject
from phi.k8s.enums.volume_type import VolumeType
from phi.k8s.resource.core.v1.volume import (
    Volume,
    AwsElasticBlockStoreVolumeSource,
    PersistentVolumeClaimVolumeSource,
    GcePersistentDiskVolumeSource,
    SecretVolumeSource,
    EmptyDirVolumeSource,
    ConfigMapVolumeSource,
    GitRepoVolumeSource,
    HostPathVolumeSource,
)
from phi.utils.log import logger


class CreateVolume(CreateK8sObject):
    volume_name: str
    app_name: str
    mount_path: str
    volume_type: VolumeType
    aws_ebs: Optional[AwsElasticBlockStoreVolumeSource] = None
    config_map: Optional[ConfigMapVolumeSource] = None
    empty_dir: Optional[EmptyDirVolumeSource] = None
    gce_persistent_disk: Optional[GcePersistentDiskVolumeSource] = None
    git_repo: Optional[GitRepoVolumeSource] = None
    host_path: Optional[HostPathVolumeSource] = None
    pvc: Optional[PersistentVolumeClaimVolumeSource] = None
    secret: Optional[SecretVolumeSource] = None

    def _create(self) -> Volume:
        """Creates the Volume resource"""

        volume = Volume(name=self.volume_name)

        if self.volume_type == VolumeType.EMPTY_DIR:
            if self.empty_dir is not None and isinstance(self.empty_dir, EmptyDirVolumeSource):
                volume.empty_dir = self.empty_dir
            else:
                volume.empty_dir = EmptyDirVolumeSource()
        elif self.volume_type == VolumeType.AWS_EBS:
            if self.aws_ebs is not None and isinstance(self.aws_ebs, AwsElasticBlockStoreVolumeSource):
                volume.aws_elastic_block_store = self.aws_ebs
            else:
                logger.error(
                    f"Volume {self.volume_type.value} selected but AwsElasticBlockStoreVolumeSource not provided."
                )
        elif self.volume_type == VolumeType.PERSISTENT_VOLUME_CLAIM:
            if self.pvc is not None and isinstance(self.pvc, PersistentVolumeClaimVolumeSource):
                volume.persistent_volume_claim = self.pvc
            else:
                logger.error(
                    f"Volume {self.volume_type.value} selected but PersistentVolumeClaimVolumeSource not provided."
                )
        elif self.volume_type == VolumeType.CONFIG_MAP:
            if self.config_map is not None and isinstance(self.config_map, ConfigMapVolumeSource):
                volume.config_map = self.config_map
            else:
                logger.error(f"Volume {self.volume_type.value} selected but ConfigMapVolumeSource not provided.")
        elif self.volume_type == VolumeType.SECRET:
            if self.secret is not None and isinstance(self.secret, SecretVolumeSource):
                volume.secret = self.secret
            else:
                logger.error(f"Volume {self.volume_type.value} selected but SecretVolumeSource not provided.")
        elif self.volume_type == VolumeType.GCE_PERSISTENT_DISK:
            if self.gce_persistent_disk is not None and isinstance(
                self.gce_persistent_disk, GcePersistentDiskVolumeSource
            ):
                volume.gce_persistent_disk = self.gce_persistent_disk
            else:
                logger.error(
                    f"Volume {self.volume_type.value} selected but GcePersistentDiskVolumeSource not provided."
                )
        elif self.volume_type == VolumeType.GIT_REPO:
            if self.git_repo is not None and isinstance(self.git_repo, GitRepoVolumeSource):
                volume.git_repo = self.git_repo
            else:
                logger.error(f"Volume {self.volume_type.value} selected but GitRepoVolumeSource not provided.")
        elif self.volume_type == VolumeType.HOST_PATH:
            if self.host_path is not None and isinstance(self.host_path, HostPathVolumeSource):
                volume.host_path = self.host_path
            else:
                logger.error(f"Volume {self.volume_type.value} selected but HostPathVolumeSource not provided.")

        # logger.debug(f"Created Volume resource: {volume}")
        return volume
