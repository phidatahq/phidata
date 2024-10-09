from fastapi import APIRouter

from api.routes.status import status_router
from api.routes.assistants import assistants_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(status_router)
v1_router.include_router(assistants_router)
