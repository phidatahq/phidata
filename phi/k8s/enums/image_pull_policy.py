from phi.utils.enum import ExtendedEnum


class ImagePullPolicy(ExtendedEnum):
    ALWAYS = "Always"
    IF_NOT_PRESENT = "IfNotPresent"
    NEVER = "Never"
