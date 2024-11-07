import base64
from typing import List, Optional, AsyncGenerator, Dict, cast, Union, Generator

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse

from phi.agent.agent import Agent, RunResponse
from phi.agent.session import AgentSession
from phi.playground.operator import format_tools, get_agent_by_id, get_session_title
from phi.utils.log import logger

from phi.playground.schemas import (
    AgentGetResponse,
    AgentRunRequest,
    AgentSessionsRequest,
    AgentSessionsResponse,
    AgentRenameRequest,
    AgentModel,
    AgentSessionDeleteRequest,
)


def get_playground_router(agents: List[Agent]) -> APIRouter:
    playground_router = APIRouter(prefix="/playground", tags=["Playground"])

    @playground_router.get("/status")
    def playground_status():
        return {"playground": "available"}

    @playground_router.get("/agent/get", response_model=List[AgentGetResponse])
    def agent_get():
        agent_list = []
        for agent in agents:
            agent_tools = agent.get_tools()
            formatted_tools = format_tools(agent_tools)

            name = agent.model.name or agent.model.__class__.__name__ if agent.model else None
            provider = agent.model.provider or agent.model.__class__.__name__ if agent.model else None
            model_id = agent.model.id if agent.model else None

            if provider and model_id:
                provider = f"{provider} {model_id}"
            elif name and model_id:
                provider = f"{name} {model_id}"
            elif model_id:
                provider = model_id
            else:
                provider = ""

            agent_list.append(
                AgentGetResponse(
                    agent_id=agent.agent_id,
                    name=agent.name,
                    model=AgentModel(
                        name=name,
                        model=model_id,
                        provider=provider,
                    ),
                    add_context=agent.add_context,
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
        run_response = agent.run(message, images=images, stream=True, stream_intermediate_steps=True)
        for run_response_chunk in run_response:
            run_response_chunk = cast(RunResponse, run_response_chunk)
            yield run_response_chunk.model_dump_json()

    def process_image(file: UploadFile) -> List[Union[str, Dict]]:
        content = file.file.read()
        encoded = base64.b64encode(content).decode("utf-8")

        image_info = {"filename": file.filename, "content_type": file.content_type, "size": len(content)}

        return [encoded, image_info]

    @playground_router.post("/agent/run")
    def agent_run(body: AgentRunRequest):
        logger.debug(f"AgentRunRequest: {body}")
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        if body.session_id is not None:
            logger.debug(f"Continuing session: {body.session_id}")
        else:
            logger.debug("Creating new session")

        # Create a new instance of this agent
        new_agent_instance = agent.deep_copy(update={"session_id": body.session_id})
        if body.user_id is not None:
            new_agent_instance.user_id = body.user_id

        if body.monitor:
            new_agent_instance.monitoring = True
        else:
            new_agent_instance.monitoring = False

        base64_image: Optional[List[Union[str, Dict]]] = None
        if body.image:
            base64_image = process_image(body.image)

        if body.stream:
            return StreamingResponse(
                chat_response_streamer(new_agent_instance, body.message, base64_image),
                media_type="text/event-stream",
            )
        else:
            run_response = cast(RunResponse, new_agent_instance.run(body.message, images=base64_image, stream=False))
            return run_response.model_dump_json()

    @playground_router.post("/agent/sessions/all")
    def get_agent_sessions(body: AgentSessionsRequest):
        logger.debug(f"AgentSessionsRequest: {body}")
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content="Agent not found.")

        if agent.storage is None:
            return JSONResponse(status_code=404, content="Agent does not have storage enabled.")

        agent_sessions: List[AgentSessionsResponse] = []
        all_agent_sessions: List[AgentSession] = agent.storage.get_all_sessions(user_id=body.user_id)
        for session in all_agent_sessions:
            title = get_session_title(session)
            agent_sessions.append(
                AgentSessionsResponse(
                    title=title,
                    session_id=session.session_id,
                    session_name=session.session_data.get("session_name") if session.session_data else None,
                    created_at=session.created_at,
                )
            )
        return agent_sessions

    @playground_router.post("/agent/sessions/{session_id}")
    def get_agent_session(session_id: str, body: AgentSessionsRequest):
        logger.debug(f"AgentSessionsRequest: {body}")
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content="Agent not found.")

        if agent.storage is None:
            return JSONResponse(status_code=404, content="Agent does not have storage enabled.")

        agent_session: Optional[AgentSession] = agent.storage.read(session_id)
        if agent_session is None:
            return JSONResponse(status_code=404, content="Session not found.")

        return agent_session

    @playground_router.post("/agent/session/rename")
    def agent_rename(body: AgentRenameRequest):
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content=f"couldn't find agent with {body.agent_id}")

        agent.session_id = body.session_id
        agent.rename_session(body.name)
        return JSONResponse(content={"message": f"successfully renamed agent {agent.name}"})

    @playground_router.post("/agent/session/delete")
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

    return playground_router


def get_async_playground_router(agents: List[Agent]) -> APIRouter:
    playground_router = APIRouter(prefix="/playground", tags=["Playground"])

    @playground_router.get("/status")
    async def playground_status():
        return {"playground": "available"}

    @playground_router.get("/agent/get", response_model=List[AgentGetResponse])
    async def agent_get():
        agent_list = []
        for agent in agents:
            agent_tools = agent.get_tools()
            formatted_tools = format_tools(agent_tools)

            name = agent.model.name or agent.model.__class__.__name__ if agent.model else None
            provider = agent.model.provider or agent.model.__class__.__name__ if agent.model else None
            model_id = agent.model.id if agent.model else None

            if provider and model_id:
                provider = f"{provider} {model_id}"
            elif name and model_id:
                provider = f"{name} {model_id}"
            elif model_id:
                provider = model_id
            else:
                provider = ""

            agent_list.append(
                AgentGetResponse(
                    agent_id=agent.agent_id,
                    name=agent.name,
                    model=AgentModel(
                        name=name,
                        model=model_id,
                        provider=provider,
                    ),
                    add_context=agent.add_context,
                    tools=formatted_tools,
                    memory={"name": agent.memory.db.__class__.__name__} if agent.memory and agent.memory.db else None,
                    storage={"name": agent.storage.__class__.__name__} if agent.storage else None,
                    knowledge={"name": agent.knowledge.__class__.__name__} if agent.knowledge else None,
                    description=agent.description,
                    instructions=agent.instructions,
                )
            )

        return agent_list

    async def chat_response_streamer(
        agent: Agent, message: str, images: Optional[List[Union[str, Dict]]] = None
    ) -> AsyncGenerator:
        run_response = await agent.arun(message, images=images, stream=True, stream_intermediate_steps=True)
        async for run_response_chunk in run_response:
            run_response_chunk = cast(RunResponse, run_response_chunk)
            yield run_response_chunk.model_dump_json()

    async def process_image(file: UploadFile) -> List[Union[str, Dict]]:
        content = file.file.read()
        encoded = base64.b64encode(content).decode("utf-8")

        image_info = {"filename": file.filename, "content_type": file.content_type, "size": len(content)}

        return [encoded, image_info]

    @playground_router.post("/agent/run")
    async def agent_run(body: AgentRunRequest):
        logger.debug(f"AgentRunRequest: {body}")
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        if body.session_id is not None:
            logger.debug(f"Continuing session: {body.session_id}")
        else:
            logger.debug("Creating new session")

        # Create a new instance of this agent
        new_agent_instance = agent.deep_copy(update={"session_id": body.session_id})
        if body.user_id is not None:
            new_agent_instance.user_id = body.user_id

        if body.monitor:
            new_agent_instance.monitoring = True
        else:
            new_agent_instance.monitoring = False

        base64_image: Optional[List[Union[str, Dict]]] = None
        if body.image:
            base64_image = await process_image(body.image)

        if body.stream:
            return StreamingResponse(
                chat_response_streamer(new_agent_instance, body.message, base64_image),
                media_type="text/event-stream",
            )
        else:
            run_response = cast(
                RunResponse, await new_agent_instance.arun(body.message, images=base64_image, stream=False)
            )
            return run_response.model_dump_json()

    @playground_router.post("/agent/sessions/all")
    async def get_agent_sessions(body: AgentSessionsRequest):
        logger.debug(f"AgentSessionsRequest: {body}")
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content="Agent not found.")

        if agent.storage is None:
            return JSONResponse(status_code=404, content="Agent does not have storage enabled.")

        agent_sessions: List[AgentSessionsResponse] = []
        all_agent_sessions: List[AgentSession] = agent.storage.get_all_sessions(user_id=body.user_id)
        for session in all_agent_sessions:
            title = get_session_title(session)
            agent_sessions.append(
                AgentSessionsResponse(
                    title=title,
                    session_id=session.session_id,
                    session_name=session.session_data.get("session_name") if session.session_data else None,
                    created_at=session.created_at,
                )
            )
        return agent_sessions

    @playground_router.post("/agent/sessions/{session_id}")
    async def get_agent_session(session_id: str, body: AgentSessionsRequest):
        logger.debug(f"AgentSessionsRequest: {body}")
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content="Agent not found.")

        if agent.storage is None:
            return JSONResponse(status_code=404, content="Agent does not have storage enabled.")

        agent_session: Optional[AgentSession] = agent.storage.read(session_id, body.user_id)
        if agent_session is None:
            return JSONResponse(status_code=404, content="Session not found.")

        return agent_session

    @playground_router.post("/agent/session/rename")
    async def agent_rename(body: AgentRenameRequest):
        agent = get_agent_by_id(agents, body.agent_id)
        if agent is None:
            return JSONResponse(status_code=404, content=f"couldn't find agent with {body.agent_id}")

        agent.session_id = body.session_id
        agent.rename_session(body.name)
        return JSONResponse(content={"message": f"successfully renamed agent {agent.name}"})

    @playground_router.post("/agent/session/delete")
    async def agent_session_delete(body: AgentSessionDeleteRequest):
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

    return playground_router
