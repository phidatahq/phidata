from phidata.utils.enums import ExtendedEnum


class VolumeType(ExtendedEnum):
    AWS_EBS = "AWS_EBS"
    EMPTY_DIR = "EMPTY_DIR"
    PERSISTENT_VOLUME_CLAIM = "PERSISTENT_VOLUME_CLAIM"
    CONFIG_MAP = "CONFIG_MAP"
    SECRET = "SECRET"
    GCE_PERSISTENT_DISK = "GCE_PERSISTENT_DISK"
    GIT_REPO = "GIT_REPO"
    HOST_PATH = "HOST_PATH"
    LOCAL = "LOCAL"
    NFS = "NFS"
