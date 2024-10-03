import base64
from typing import List, Optional, Generator, Dict, cast, Union

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse

from phi.agent.agent import Agent, RunResponse
from phi.agent.session import AgentSession
from phi.playground.operator import format_tools, get_agent_by_id, get_session_title
from phi.utils.log import logger

from phi.playground.schemas import (
    AgentGetResponse,
    AgentRunRequest,
    GetAgentSessionsRequest,
    GetAgentSessionsResponse,
    AgentRenameRequest,
    AgentModel,
    AgentSessionDeleteRequest,
)


def create_playground_routes(agents: List[Agent]) -> APIRouter:
    playground_routes = APIRouter(prefix="/playground", tags=["Playground"])

    @playground_routes.get("/status")
    def playground_status():
        return {"playground": "available"}

    @playground_routes.get("/agent/get", response_model=List[AgentGetResponse])
    def agent_get():
        agent_list = []
        for agent in agents:
            agent_tools = agent.get_tools()
            formatted_tools = format_tools(agent_tools)

            agent_list.append(
                AgentGetResponse(
                    agent_id=agent.agent_id,
                    name=agent.name,
                    model=AgentModel(
                        provider=agent.model.provider or agent.model.__class__.__name__ if agent.model else None,
                        name=agent.model.name or agent.model.__class__.__name__ if agent.model else None,
                        model=agent.model.id if agent.model else None,
                    ),
                    enable_rag=agent.enable_rag,
                    tools=formatted_tools,
                    memory={"name": agent.memory.db.__class__.__name__} if agent.memory and agent.memory.db else None,
                    storage={"name": agent.storage.__class__.__name__} if agent.storage else None,
                    knowledge={"name": agent.knowledge.__class__.__name__} if agent.knowledge else None,
                    description=agent.description,
                    instructions=agent.instructions,
                )
            )

        return agent_list

    def chat_response_streamer(
        agent: Agent, message: str, images: Optional[List[Union[str, Dict]]] = None
    ) -> Generator:
        run_response = agent.run(message, images=images, stream=True)
        for run_response_chunk in run_response:
            run_response_chunk = cast(RunResponse, run_response_chunk)
            yield run_response_chunk.model_dump_json()

    def process_image(file: UploadFile) -> List[Union[str, Dict]]:
        content = file.file.read()
        encoded = base64.b64encode(content).decode("utf-8")

        image_info = {"filename": file.filename, "content_type": file.content_type, "size": len(content)}

        return [encoded, image_info]

    @playground_routes.post("/agent/run")
    def agent_run(body: AgentRunRequest):
        logger.debug(f"AgentRunRequest: {body}")
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Create a new instance of this agent
        new_agent = agent.create_copy(update={"session_id": body.session_id})
        if body.user_id:
            agent.user_id = body.user_id

        if body.monitor:
            agent.monitoring = True
        else:
            agent.monitoring = False

        base64_image: Optional[List[Union[str, Dict]]] = None
        if body.image:
            base64_image = process_image(body.image)

        if body.stream:
            return StreamingResponse(
                chat_response_streamer(new_agent, body.message, base64_image),
                media_type="text/event-stream",
            )
        else:
            run_response = cast(RunResponse, new_agent.run(body.message, images=base64_image, stream=False))
            return run_response.model_dump_json()

    @playground_routes.post("/agent/sessions/all")
    def get_agent_sessions(body: GetAgentSessionsRequest):
        logger.debug(f"GetAgentSessionsRequest: {body}")
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content="Agent not found.")

        if agent.storage is None:
            return JSONResponse(status_code=404, content="Agent does not have storage enabled.")

        agent_sessions: List[GetAgentSessionsResponse] = []
        all_agent_sessions: List[AgentSession] = agent.storage.get_all_sessions(user_id=body.user_id)
        for session in all_agent_sessions:
            title = get_session_title(session)
            agent_sessions.append(
                GetAgentSessionsResponse(session_id=session.session_id, title=title, created_at=session.created_at)
            )
        return agent_sessions

    @playground_routes.post("/agent/sessions/{session_id}")
    def get_agent_session(session_id: str, body: GetAgentSessionsRequest):
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content="Agent not found.")

        agent.session_id = session_id
        agent.read_from_storage()
        return agent.to_agent_session()

    @playground_routes.post("/agent/session/rename")
    def agent_rename(body: AgentRenameRequest):
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content=f"couldn't find agent with {body.agent_id}")

        agent.session_id = body.session_id
        agent.rename_session(body.name)
        return JSONResponse(content={"message": f"successfully renamed agent {agent.name}"})

    @playground_routes.post("/agent/session/delete")
    def agent_session_delete(body: AgentSessionDeleteRequest):
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content="Agent not found.")

        if agent.storage is None:
            return JSONResponse(status_code=404, content="Agent does not have storage enabled.")

        all_agent_sessions: List[AgentSession] = agent.storage.get_all_sessions(user_id=body.user_id)
        for session in all_agent_sessions:
            if session.session_id == body.session_id:
                agent.delete_session(body.session_id)
                return JSONResponse(content={"message": f"successfully deleted agent {agent.name}"})

        return JSONResponse(status_code=404, content="Session not found.")

    return playground_routes
