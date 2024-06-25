from enum import Enum


class InfraType(str, Enum):
    local = "local"
    docker = "docker"
    k8s = "k8s"
    aws = "aws"
