from typing import Union, Optional

from phidata.constants import AIRFLOW_EXECUTOR_ENV_VAR
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class AirflowExecutor(ExtendedEnum):
    DebugExecutor = "DebugExecutor"
    LocalExecutor = "LocalExecutor"
    SequentialExecutor = "SequentialExecutor"
    CeleryExecutor = "CeleryExecutor"
    CeleryKubernetesExecutor = "CeleryKubernetesExecutor"
    DaskExecutor = "DaskExecutor"
    KubernetesExecutor = "KubernetesExecutor"


AirflowExecutorType = Union[str, AirflowExecutor]


def get_airflow_executor() -> Optional[AirflowExecutor]:
    from os import getenv

    phidata_runtime_env_var = getenv(AIRFLOW_EXECUTOR_ENV_VAR)
    logger.debug(f"{AIRFLOW_EXECUTOR_ENV_VAR}: {phidata_runtime_env_var}")

    if (
        phidata_runtime_env_var is not None
        and phidata_runtime_env_var in AirflowExecutor.values_list()
    ):
        return AirflowExecutor.from_str(phidata_runtime_env_var)
    return AirflowExecutor.SequentialExecutor
