from phidata.utils.env_var import validate_env_vars


def airflow_installed() -> bool:
    return validate_env_vars({"INIT_AIRFLOW": True})
