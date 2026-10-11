"""Sandbox status and durable workspace downloads under agent/session authorization."""

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from agno.os.auth import require_resource_access
from agno.os.middleware.user_scope import assert_session_matches_component, get_scoped_user_id
from agno.sandbox.base import SandboxError


def add_sandbox_artifact_routes(router: APIRouter, os: Any) -> None:
    async def resolve(request: Request, agent_id: str, session_id: str) -> Any:
        agent = next(
            (
                value
                for value in os.agents or []
                if getattr(value, "_sandbox_execution", False) is True and value.get_id() == agent_id
            ),
            None,
        )
        if agent is None or agent.coordinator is None:
            raise HTTPException(404, "Sandbox agent not found")
        from agno.sandbox.artifacts import SandboxArtifacts

        session = await agent.aget_session(session_id, user_id=get_scoped_user_id(request))
        if session is None:
            raise HTTPException(404, "Sandbox session not found")
        assert_session_matches_component(session, "agents", agent_id)
        return SandboxArtifacts(agent.coordinator.store, agent.coordinator.transfer.store), session.user_id

    async def call(operation: Any) -> Any:
        from agno.sandbox.artifacts import SandboxArtifactNotFound, SandboxSessionNotFound

        try:
            return await operation
        except (SandboxSessionNotFound, SandboxArtifactNotFound):
            raise HTTPException(404, "Sandbox session or artifact not found")
        except FileNotFoundError:
            raise HTTPException(503, "Checkpoint storage is unavailable")
        except SandboxError:
            raise HTTPException(409, "Sandbox operation could not be completed")

    dependencies = [Depends(require_resource_access("agents", "run", "agent_id"))]

    @router.get("/agents/{agent_id}/sessions/{session_id}/sandbox", tags=["Agents"], dependencies=dependencies)
    async def sandbox_status(request: Request, agent_id: str, session_id: str) -> Any:
        artifacts, user_id = await resolve(request, agent_id, session_id)
        return await call(artifacts.astatus(agent_id=agent_id, session_id=session_id, user_id=user_id))

    @router.get(
        "/agents/{agent_id}/sessions/{session_id}/sandbox/artifacts", tags=["Agents"], dependencies=dependencies
    )
    async def sandbox_artifacts(
        request: Request,
        agent_id: str,
        session_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
    ) -> Any:
        artifacts, user_id = await resolve(request, agent_id, session_id)
        return await call(
            artifacts.alist(agent_id=agent_id, session_id=session_id, user_id=user_id, offset=offset, limit=limit)
        )

    @router.get("/agents/{agent_id}/sessions/{session_id}/sandbox/artifact", tags=["Agents"], dependencies=dependencies)
    async def sandbox_artifact(
        request: Request, agent_id: str, session_id: str, path: str = Query(..., max_length=4096)
    ) -> Response:
        artifacts, user_id = await resolve(request, agent_id, session_id)
        artifact = await call(artifacts.aread(path, agent_id=agent_id, session_id=session_id, user_id=user_id))
        filename = quote(path.rsplit("/", 1)[-1], safe="")
        return Response(
            artifact.content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''" + filename,
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, no-store",
                "X-Agno-Checkpoint": artifact.checkpoint,
                "X-Agno-Run-ID": quote(artifact.run_id, safe=""),
            },
        )

    async def lifecycle(request: Request, agent_id: str, session_id: str) -> Any:
        _, user_id = await resolve(request, agent_id, session_id)
        from agno.sandbox.lifecycle import SandboxLifecycle

        agent = next(
            value
            for value in os.agents
            if getattr(value, "_sandbox_execution", False) is True and value.get_id() == agent_id
        )
        return SandboxLifecycle(agent.coordinator), agent, user_id

    @router.post("/agents/{agent_id}/sessions/{session_id}/sandbox/retire", tags=["Agents"], dependencies=dependencies)
    async def retire_sandbox(request: Request, agent_id: str, session_id: str) -> Any:
        operations, agent, user_id = await lifecycle(request, agent_id, session_id)
        return await call(operations.aretire(agent._spec(session_id), user_id=user_id))

    @router.delete(
        "/agents/{agent_id}/sessions/{session_id}/sandbox/recovery", tags=["Agents"], dependencies=dependencies
    )
    async def delete_sandbox_recovery(request: Request, agent_id: str, session_id: str) -> Any:
        operations, _, user_id = await lifecycle(request, agent_id, session_id)
        return await call(operations.adelete_recovery(agent_id=agent_id, session_id=session_id, user_id=user_id))
