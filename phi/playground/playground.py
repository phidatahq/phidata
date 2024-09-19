from typing import List, Optional, Generator, Any, Dict, cast

from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRouter
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from phi.agent.agent import Agent, RunResponse, Tool, Toolkit, Function
from phi.playground.settings import PlaygroundSettings
from phi.utils.log import logger


class AgentModel(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class AgentGetResponse(BaseModel):
    agent_id: str
    name: Optional[str] = None
    model: Optional[AgentModel] = None
    enable_rag: Optional[bool] = None
    tools: Optional[List[Dict[str, Any]]] = None
    memory: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None
    knowledge: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    instructions: Optional[List[str]] = None


class AgentRunRequest(BaseModel):
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
        router: Optional[APIRouter] = None,
    ):
        self.agents: List[Agent] = agents
        self.settings: PlaygroundSettings = settings or PlaygroundSettings()
        self.api_app: Optional[FastAPI] = api_app
        self.router: Optional[APIRouter] = router

        self.agent_list: Optional[List[AgentGetResponse]] = None

    def get_router(self):
        playground_routes = APIRouter(prefix="/playground", tags=["Playground"])

        @playground_routes.get("/status")
        def playground_status():
            return {"playground": "available"}

        @playground_routes.get("/agent/get", response_model=List[AgentGetResponse])
        def agent_get():
            if self.agent_list is not None:
                return self.agent_list

            self.agent_list = []
            for agent in self.agents:
                agent_tools = agent.get_tools()
                formatted_tools = []
                if agent_tools is not None:
                    for tool in agent_tools:
                        if isinstance(tool, dict):
                            formatted_tools.append(tool)
                        elif isinstance(tool, Tool):
                            formatted_tools.append(tool.to_dict())
                        elif isinstance(tool, Toolkit):
                            for f_name, f in tool.functions.items():
                                formatted_tools.append(f.to_dict())
                        elif isinstance(tool, Function):
                            formatted_tools.append(tool.to_dict())
                        elif callable(tool):
                            func = Function.from_callable(tool)
                            formatted_tools.append(func.to_dict())
                        else:
                            logger.warning(f"Unknown tool type: {type(tool)}")

                self.agent_list.append(
                    AgentGetResponse(
                        agent_id=agent.agent_id,
                        name=agent.name,
                        model=AgentModel(
                            provider=agent.model.provider or agent.model.__class__.__name__ if agent.model else None,
                            name=agent.model.name or agent.model.__class__.__name__ if agent.model else None,
                            model=agent.model.model if agent.model else None,
                        ),
                        enable_rag=agent.enable_rag,
                        tools=formatted_tools,
                        memory={"name": agent.memory.db.__class__.__name__}
                        if agent.memory and agent.memory.db
                        else None,
                        storage={"name": agent.storage.__class__.__name__} if agent.storage else None,
                        knowledge={"name": agent.knowledge.__class__.__name__} if agent.knowledge else None,
                        description=agent.description,
                        instructions=agent.instructions,
                    )
                )

            return self.agent_list

        def chat_response_streamer(agent: Agent, message: str) -> Generator:
            run_response = agent.run(message, stream=True)
            for run_response_chunk in run_response:
                run_response_chunk = cast(RunResponse, run_response_chunk)
                yield run_response_chunk.model_dump_json()

        @playground_routes.post("/agent/run")
        def agent_chat(body: AgentRunRequest):
            logger.debug(f"AgentRunRequest: {body}")
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
                run_response = cast(RunResponse, agent.run(body.message, stream=False))
                return run_response.model_dump_json()

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
        if not self.router:
            self.router = APIRouter(prefix="/v1")

        if not self.router:
            raise Exception("API Router could not be created.")

        self.router.include_router(self.get_router())
        self.api_app.include_router(self.router)

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
