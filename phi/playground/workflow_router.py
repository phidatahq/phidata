from typing import List, Dict, Any, Optional

from fastapi import HTTPException
from fastapi.routing import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse

from phi.playground.operator import get_session_title_from_workflow_session, get_workflow_by_id
from phi.playground.schemas import WorkflowRunRequest, WorkflowSessionsRequest, WorkflowRenameRequest
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

    @workflow_router.get("/workflow/input_fields/{workflow_id}")
    def get_input_fields(workflow_id: str):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        response = workflow._run_parameters
        response["workflow_id"] = workflow.workflow_id
        response["name"] = workflow.name
        response["description"] = workflow.description
        return response

    @workflow_router.get("/workflow/config/{workflow_id}")
    def get_config(workflow_id: str):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {
            "storage": workflow.storage.__class__.__name__ if workflow.storage else None,
        }

    @workflow_router.post("/workflow/{workflow_id}/run")
    def run_workflow(workflow_id: str, body: WorkflowRunRequest):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow.user_id = body.user_id
        if workflow._run_return_type == "RunResponse":
            return workflow.run(**body.input)
        return StreamingResponse((r.model_dump_json() for r in workflow.run(**body.input)), media_type="text/event-stream")

    @workflow_router.post("/workflow/{workflow_id}/session/all")
    def get_all_workflow_sessions(workflow_id: str, body: WorkflowSessionsRequest):
        workflow = get_workflow_by_id(workflows, workflow_id)

        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.storage is None:
            raise HTTPException(status_code=404, detail="Workflow does not have storage enabled")

        workflow_sessions: List[Dict[str, Any]] = []
        all_workflow_sessions: List[WorkflowSession] = workflow.storage.get_all_sessions(
            user_id=body.user_id, workflow_id=workflow_id
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

    @workflow_router.post("/workflow/{workflow_id}/session/{session_id}")
    def get_workflow_session(workflow_id: str, session_id: str, body: WorkflowSessionsRequest):
        workflow = get_workflow_by_id(workflows, workflow_id)

        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.storage is None:
            raise HTTPException(status_code=404, detail="Workflow does not have storage enabled")

        workflow_session: Optional[WorkflowSession] = workflow.storage.read(session_id, body.user_id)
        if workflow_session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return workflow_session

    @workflow_router.post("/workflow/{workflow_id}/session/{session_id}/rename")
    def workflow_rename(workflow_id: str, session_id: str, body: WorkflowRenameRequest):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow.rename_session(session_id, body.name)
        return JSONResponse(content={"message": f"successfully renamed workflow {workflow.name}"})

    @workflow_router.post("/workflow/{workflow_id}/session/{session_id}/delete")
    def workflow_delete(workflow_id: str, session_id: str):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow.delete_session(session_id)
        return JSONResponse(content={"message": f"successfully deleted workflow {workflow.name}"})

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

    @workflow_router.get("/workflow/input_fields/{workflow_id}")
    async def get_input_fields(workflow_id: str):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        response = workflow._run_parameters
        response["workflow_id"] = workflow.workflow_id
        response["name"] = workflow.name
        response["description"] = workflow.description
        return response

    @workflow_router.get("/workflow/config/{workflow_id}")
    async def get_config(workflow_id: str):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {
            "storage": workflow.storage.__class__.__name__ if workflow.storage else None,
        }

    @workflow_router.post("/workflow/{workflow_id}/run")
    async def run_workflow(workflow_id: str, body: WorkflowRunRequest):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow.user_id = body.user_id
        if workflow._run_return_type == "RunResponse":
            return workflow.run(**body.input)
        return StreamingResponse((r.model_dump_json() for r in workflow.run(**body.input)), media_type="text/event-stream")

    @workflow_router.post("/workflow/{workflow_id}/session/all")
    async def get_all_workflow_sessions(workflow_id: str, body: WorkflowSessionsRequest):
        workflow = get_workflow_by_id(workflows, workflow_id)

        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.storage is None:
            raise HTTPException(status_code=404, detail="Workflow does not have storage enabled")

        workflow_sessions: List[Dict[str, Any]] = []
        all_workflow_sessions: List[WorkflowSession] = workflow.storage.get_all_sessions(
            user_id=body.user_id, workflow_id=workflow_id
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

    @workflow_router.post("/workflow/{workflow_id}/session/{session_id}")
    async def get_workflow_session(workflow_id: str, session_id: str, body: WorkflowSessionsRequest):
        workflow = get_workflow_by_id(workflows, workflow_id)

        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.storage is None:
            raise HTTPException(status_code=404, detail="Workflow does not have storage enabled")

        workflow_session: Optional[WorkflowSession] = workflow.storage.read(session_id, body.user_id)
        if workflow_session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return workflow_session

    @workflow_router.post("/workflow/{workflow_id}/session/{session_id}/rename")
    async def workflow_rename(workflow_id: str, session_id: str, body: WorkflowRenameRequest):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow.rename_session(session_id, body.name)
        return JSONResponse(content={"message": f"successfully renamed workflow {workflow.name}"})

    @workflow_router.post("/workflow/{workflow_id}/session/{session_id}/delete")
    async def workflow_delete(workflow_id: str, session_id: str):
        workflow = get_workflow_by_id(workflows, workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow.delete_session(session_id)
        return JSONResponse(content={"message": f"successfully deleted workflow {workflow.name}"})

    return workflow_router
