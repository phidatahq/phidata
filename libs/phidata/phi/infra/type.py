from enum import Enum


class InfraType(str, Enum):
    local = "local"
    docker = "docker"
    aws = "aws"
