from phi.utils.enum import ExtendedEnum


class StorageClassType(str, ExtendedEnum):
    GCE_SSD = "GCE_SSD"
    GCE_STANDARD = "GCE_STANDARD"
