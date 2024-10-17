from fastapi import APIRouter

from utils.dttm import current_utc_str

######################################################
## Router for health checks
######################################################

health_check_router = APIRouter(tags=["Health"])


@health_check_router.get("/health")
def get_health():
    """Check the health of the Api"""

    return {
        "status": "success",
        "router": "health",
        "path": "/health",
        "utc": current_utc_str(),
    }
