# Need to be sure that we don't import anything which may lead to circular imports
from typing import Any, List, Optional, Type


def get_default_ns_name(app_name: str) -> str:
    return "{}-ns".format(app_name)


def get_default_ctx_name(app_name: str) -> str:
    return "{}-ctx".format(app_name)


def get_default_sa_name(app_name: str) -> str:
    return "{}-sa".format(app_name)


def get_default_cr_name(app_name: str) -> str:
    return "{}-cr".format(app_name)


def get_default_crb_name(app_name: str) -> str:
    return "{}-crb".format(app_name)


def get_default_pod_name(app_name: str) -> str:
    return "{}-pod".format(app_name)


def get_default_container_name(app_name: str) -> str:
    return "{}-container".format(app_name)


def get_default_service_name(app_name: str) -> str:
    return "{}-svc".format(app_name)


def get_default_deploy_name(app_name: str) -> str:
    return "{}-deploy".format(app_name)


def get_default_configmap_name(app_name: str) -> str:
    return "{}-cm".format(app_name)


def get_default_secret_name(app_name: str) -> str:
    return "{}-secret".format(app_name)


def get_default_volume_name(app_name: str) -> str:
    return "{}-volume".format(app_name)


def get_default_pvc_name(app_name: str) -> str:
    return "{}-pvc".format(app_name)


def get_image_str(repo: str, tag: str) -> str:
    return f"{repo}:{tag}"


def isinstanceany(obj: Any, class_list: List[Type]) -> bool:
    for cls in class_list:
        if isinstance(obj, cls):
            return True
    return False


def str_to_int(inp: str) -> Optional[int]:
    """
    Safely converts a string value to integer.
    Args:
        inp: input string

    Returns: input string as int if possible, None if not
    """
    try:
        val = int(inp)
        return val
    except Exception:
        return None


def is_empty(val: Any) -> bool:
    if val is None or len(val) == 0 or val == "":
        return True
    return False
