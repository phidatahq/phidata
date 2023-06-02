from phidata.utils.enums import ExtendedEnum


class WorkspaceVolumeType(ExtendedEnum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    AwsEbs = "AwsEbs"
    AwsEfs = "AwsEfs"
    PersistentVolume = "PersistentVolume"
