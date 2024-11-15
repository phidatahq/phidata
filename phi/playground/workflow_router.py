
from fastapi.routing import APIRouter

from phi.workflow.workflow import Workflow


def get_workflow_router(workflow: Workflow) -> APIRouter:
    workflow_router = APIRouter(prefix="/workflow_playground", tags=["Workflow Playground"])

    @workflow_router.get("/status")
    def workflow_status():
        return {"workflow_playground": "available"}
    
    @workflow_router.get("/input_fields")
    def get_input_fields():
        return workflow._run_parameters

    return workflow_router


def get_async_workflow_router(workflow: Workflow) -> APIRouter:
    workflow_router = APIRouter(prefix="/workflow_playground", tags=["Workflow Playground"])

    @workflow_router.get("/status")
    async def workflow_status():
        return {"workflow_playground": "available"}
    
    @workflow_router.get("/input_fields")
    async def get_input_fields():
        return workflow._run_parameters

    return workflow_router
