from typing import Literal, Optional

from phidata.constants import PHIDATA_RUNTIME_ENV_VAR
from phidata.utils.enums import ExtendedEnum


class PhidataRuntimeType(ExtendedEnum):
    local = "local"
    airflow = "airflow"
    jupyter = "jupyter"
    superset = "superset"
    databox = "databox"

    def is_remote_runtime(self) -> bool:
        return self in (
            PhidataRuntimeType.airflow,
            PhidataRuntimeType.jupyter,
            PhidataRuntimeType.superset,
            PhidataRuntimeType.databox,
        )


def get_phidata_runtime() -> Optional[PhidataRuntimeType]:
    from os import getenv

    phidata_runtime_env = getenv(PHIDATA_RUNTIME_ENV_VAR)
    # logger.debug(f"{PHIDATA_RUNTIME_ENV_VAR}: {phidata_runtime_env}")

    if (
        phidata_runtime_env is not None
        and phidata_runtime_env in PhidataRuntimeType.values_list()
    ):
        return PhidataRuntimeType.from_str(phidata_runtime_env)
    return PhidataRuntimeType.local
