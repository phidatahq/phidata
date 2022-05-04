from phidata.utils.enums import ExtendedEnum


class RestartPolicy(ExtendedEnum):
    ALWAYS = "Always"
    ON_FAILURE = "OnFailure"
    NEVER = "Never"
