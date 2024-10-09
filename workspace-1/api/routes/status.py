from fastapi import APIRouter

from api.routes.endpoints import endpoints
from utils.dttm import current_utc_str

######################################################
## Router for health checks
######################################################

status_router = APIRouter(tags=["Status"])


@status_router.get(endpoints.PING)
def status_ping():
    """Ping the Api"""

    return {"ping": "pong"}


@status_router.get(endpoints.HEALTH)
def status_health():
    """Check the health of the Api"""

    return {
        "status": "success",
        "router": "status",
        "path": endpoints.HEALTH,
        "utc": current_utc_str(),
    }
