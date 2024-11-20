from typing import List, Dict, Any, Optional

from fastapi import HTTPException
from fastapi.routing import APIRouter
from fastapi.responses import StreamingResponse

from phi.playground.operator import get_session_title_from_workflow_session
from phi.playground.schemas import WorkflowSessionsRequest
from phi.workflow.session import WorkflowSession
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
                if workflow._run_return_type == "RunResponse":
                    return workflow.run(**input)
                else:
                    return StreamingResponse(
                        (r.model_dump_json() for r in workflow.run(**input)), media_type="text/event-stream"
                    )
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    @workflow_router.post("/workflow/session/all/{workflow_id}")
    def get_all_workflow_sessions(workflow_id: str, body: WorkflowSessionsRequest):
        workflow = None
        for _workflow in workflows:
            if _workflow.workflow_id == workflow_id:
                workflow = _workflow
                break

        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow_sessions: List[Dict[str, Any]] = []
        all_workflow_sessions: List[WorkflowSession] = workflow.storage.get_all_sessions(
            user_id=body.user_id
        )
        for session in all_workflow_sessions:
            workflow_sessions.append(
                {
                    "title": get_session_title_from_workflow_session(session),
                    "session_id": session.session_id,
                    "session_name": session.session_data.get("session_name") if session.session_data else None,
                    "created_at": session.created_at,
                }
            )
        return workflow_sessions
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
                        (r.model_dump_json() for r in workflow.run(**input)), media_type="text/event-stream"
                    )
        raise HTTPException(status_code=404, detail="Workflow not found")

    @workflow_router.post("/workflow/session/all/{workflow_id}")
    async def get_all_workflow_sessions(workflow_id: str, body: WorkflowSessionsRequest):
        workflow = None
        for _workflow in workflows:
            if _workflow.workflow_id == workflow_id:
                workflow = _workflow
                break

        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow_sessions: List[Dict[str, Any]] = []
        all_workflow_sessions: List[WorkflowSession] = workflow.storage.get_all_sessions(
            user_id=body.user_id
        )
        for session in all_workflow_sessions:
            workflow_sessions.append(
                {
                    "title": get_session_title_from_workflow_session(session),
                    "session_id": session.session_id,
                    "session_name": session.session_data.get("session_name") if session.session_data else None,
                    "created_at": session.created_at,
                }
            )
        return workflow_sessions

    return workflow_router
