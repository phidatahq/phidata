from phi.utils.enum import ExtendedEnum


class Protocol(str, ExtendedEnum):
    UDP = "UDP"
    TCP = "TCP"
    SCTP = "SCTP"
