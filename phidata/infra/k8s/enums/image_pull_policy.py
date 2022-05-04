from phidata.utils.enums import ExtendedEnum


class ImagePullPolicy(ExtendedEnum):
    ALWAYS = "Always"
    IF_NOT_PRESENT = "IfNotPresent"
    NEVER = "Never"
