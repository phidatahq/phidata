from phi.utils.enum import ExtendedEnum


class ImagePullPolicy(str, ExtendedEnum):
    ALWAYS = "Always"
    IF_NOT_PRESENT = "IfNotPresent"
    NEVER = "Never"
