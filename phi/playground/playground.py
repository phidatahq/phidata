from typing import List, Optional, Generator

from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRouter
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from phi.agent.agent import Agent
from phi.playground.settings import PlaygroundSettings
from phi.utils.log import logger


class AgentLLM(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class AgentGetResponse(BaseModel):
    agent_id: str
    llm: Optional[AgentLLM] = None
    name: Optional[str] = None


class AgentChatRequest(BaseModel):
    message: str
    agent_id: str
    stream: bool = True
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class Playground:
    def __init__(
        self,
        agents: List[Agent],
        settings: Optional[PlaygroundSettings] = None,
        api_app: Optional[FastAPI] = None,
        api_router: Optional[APIRouter] = None,
    ):
        self.agents: List[Agent] = agents
        self.settings: PlaygroundSettings = settings or PlaygroundSettings()
        self.api_app: Optional[FastAPI] = api_app
        self.api_router: Optional[APIRouter] = api_router

    def get_api_router(self):
        playground_routes = APIRouter(prefix="/playground", tags=["Playground"])

        @playground_routes.get("/status")
        def playground_status():
            return {"playground": "available"}

        @playground_routes.get("/agent/get", response_model=List[AgentGetResponse])
        def agent_get():
            agent_list: List[AgentGetResponse] = []
            for agent in self.agents:
                agent_list.append(
                    AgentGetResponse(
                        llm=AgentLLM(
                            provider=agent.llm.provider or agent.llm.__class__.__name__,
                            name=agent.llm.name or agent.llm.__class__.__name__,
                            model=agent.llm.model,
                        ),
                        name=agent.name,
                        agent_id=agent.agent_id,
                    )
                )

            return agent_list

        def chat_response_streamer(agent: Agent, message: str) -> Generator:
            for chunk in agent.run(message):
                yield chunk

        @playground_routes.post("/agent/chat")
        def agent_chat(body: AgentChatRequest):
            logger.debug(f"ChatRequest: {body}")
            agent: Optional[Agent] = None
            for _agent in self.agents:
                if _agent.agent_id == body.agent_id:
                    agent = _agent
                    break
            if agent is None:
                raise HTTPException(status_code=404, detail="Agent not found")

            if body.stream:
                return StreamingResponse(
                    chat_response_streamer(agent, body.message),
                    media_type="text/event-stream",
                )
            else:
                return agent.run(body.message, stream=False)

        return playground_routes

    def get_api_app(self) -> FastAPI:
        """Create a FastAPI App for the Playground

        Returns:
            FastAPI: FastAPI App
        """
        from starlette.middleware.cors import CORSMiddleware

        # Create a FastAPI App if not provided
        if not self.api_app:
            self.api_app = FastAPI(
                title=self.settings.title,
                docs_url="/docs" if self.settings.docs_enabled else None,
                redoc_url="/redoc" if self.settings.docs_enabled else None,
                openapi_url="/openapi.json" if self.settings.docs_enabled else None,
            )

        if not self.api_app:
            raise Exception("API App could not be created.")

        # Create an API Router if not provided
        if not self.api_router:
            self.api_router = APIRouter(prefix="/v1")

        if not self.api_router:
            raise Exception("API Router could not be created.")

        self.api_router.include_router(self.get_api_router())
        self.api_app.include_router(self.api_router)

        # Add Middlewares
        self.api_app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

        return self.api_app

    def serve(
        self,
        app: Optional[str] = None,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        reload: bool = False,
        **kwargs,
    ):
        import uvicorn
        from phi.api.playground import create_playground_endpoint, PlaygroundEndpointCreate

        _app = app or self.api_app
        if _app is None:
            _app = self.get_api_app()

        _host = host or "0.0.0.0"
        _port = port or 7777

        try:
            create_playground_endpoint(
                playground=PlaygroundEndpointCreate(endpoint=f"http://{_host}:{_port}"),
            )
        except Exception as e:
            logger.error(f"Could not create Playground Endpoint: {e}")
            logger.error("Please try again.")
            return

        uvicorn.run(app=_app, host=_host, port=_port, reload=reload, **kwargs)
