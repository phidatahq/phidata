from typing import Optional

from phidata.constants import PHIDATA_RUNTIME_ENV_VAR
from phidata.utils.enums import ExtendedEnum


class PhidataRuntimeType(ExtendedEnum):
    local = "local"
    docker = "docker"
    kubernetes = "kubernetes"


def get_phidata_runtime() -> Optional[PhidataRuntimeType]:
    from os import getenv

    phidata_runtime_env_var = getenv(PHIDATA_RUNTIME_ENV_VAR)
    # logger.debug(f"{PHIDATA_RUNTIME_ENV_VAR}: {phidata_runtime_env_var}")

    if (
        phidata_runtime_env_var is not None
        and phidata_runtime_env_var in PhidataRuntimeType.values_list()
    ):
        return PhidataRuntimeType.from_str(phidata_runtime_env_var)
    return PhidataRuntimeType.local
