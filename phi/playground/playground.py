from fastapi import FastAPI
from typing import List, Optional
from fastapi.routing import APIRouter

from phi.agent.agent import Agent
from phi.playground.settings import PlaygroundSettings


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
        agent_router = APIRouter(prefix="/agent", tags=["Agent"])

        @agent_router.get("/health")
        def agent_run_health():
            return {"status": "success", "path": "/agent/health"}

        return agent_router

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

        _app = app or self.api_app
        if _app is None:
            _app = self.get_api_app()

        _host = host or "0.0.0.0"
        _port = port or 8000

        uvicorn.run(app=_app, host=_host, port=_port, reload=reload, **kwargs)
