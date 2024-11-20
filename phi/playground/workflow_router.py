from typing import List, Dict, Any

from fastapi import HTTPException
from fastapi.routing import APIRouter
from fastapi.responses import StreamingResponse

from phi.workflow.workflow import Workflow


def get_workflow_router(workflows: List[Workflow]) -> APIRouter:
    workflow_router = APIRouter(prefix="/workflow_playground", tags=["Workflow Playground"])

    @workflow_router.get("/status")
    def workflow_status():
        return {"workflow_playground": "available"}

    @workflow_router.get("/workflows")
    def get_workflows():
        return [
            {"id": workflow.workflow_id, "name": workflow.name, "description": workflow.description}
            for workflow in workflows
        ]

    @workflow_router.get("/input_fields/{workflow_id}")
    def get_input_fields(workflow_id: str):
        for workflow in workflows:
            if workflow.workflow_id == workflow_id:
                return workflow._run_parameters
        raise HTTPException(status_code=404, detail="Workflow not found")

    @workflow_router.get("/config/{workflow_id}")
    def get_config(workflow_id: str):
        for workflow in workflows:
            if workflow.workflow_id == workflow_id:
                return {
                    "memory": workflow.memory.__class__.__name__ if workflow.memory else None,
                    "storage": workflow.storage.__class__.__name__ if workflow.storage else None,
                }
        raise HTTPException(status_code=404, detail="Workflow not found")

    @workflow_router.post("/run/{workflow_id}")
    def run_workflow(workflow_id: str, input: Dict[str, Any]):
        for workflow in workflows:
            if workflow.workflow_id == workflow_id:
                print(f"*********** Running workflow: {workflow._run_return_type} ***********")
        raise HTTPException(status_code=404, detail="Workflow not found")

    return workflow_router


def get_async_workflow_router(workflows: List[Workflow]) -> APIRouter:
    workflow_router = APIRouter(prefix="/workflow_playground", tags=["Workflow Playground"])

    @workflow_router.get("/status")
    async def workflow_status():
        return {"workflow_playground": "available"}

    @workflow_router.get("/workflows")
    async def get_workflows():
        return [
            {"id": workflow.workflow_id, "name": workflow.name, "description": workflow.description}
            for workflow in workflows
        ]

    @workflow_router.get("/input_fields/{workflow_id}")
    async def get_input_fields(workflow_id: str):
        for workflow in workflows:
            if workflow.workflow_id == workflow_id:
                return workflow._run_parameters
        raise HTTPException(status_code=404, detail="Workflow not found")

    @workflow_router.get("/config/{workflow_id}")
    async def get_config(workflow_id: str):
        for workflow in workflows:
            if workflow.workflow_id == workflow_id:
                return {
                    "memory": workflow.memory.__class__.__name__ if workflow.memory else None,
                    "storage": workflow.storage.__class__.__name__ if workflow.storage else None,
                }
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    @workflow_router.post("/run/{workflow_id}")
    async def run_workflow(workflow_id: str, input: Dict[str, Any]):
        for workflow in workflows:
            if workflow.workflow_id == workflow_id:
                if workflow._run_return_type == "RunResponse":
                    return workflow.run(**input)
                else:
                    return StreamingResponse(
                        (r.model_dump_json() for r in workflow.run(**input)),
                        media_type="text/event-stream"
                    )
        raise HTTPException(status_code=404, detail="Workflow not found")

    return workflow_router
