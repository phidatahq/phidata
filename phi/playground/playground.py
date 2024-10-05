from typing import List, Optional

from fastapi import FastAPI
from fastapi.routing import APIRouter

from phi.agent.agent import Agent
from phi.api.playground import create_playground_endpoint, PlaygroundEndpointCreate
from phi.playground.routes import create_playground_routes
from phi.playground.settings import PlaygroundSettings
from phi.utils.log import logger


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

    def get_router(self):
        return create_playground_routes(self.agents)

    def get_api_app(self) -> FastAPI:
        from starlette.middleware.cors import CORSMiddleware

        if not self.api_app:
            self.api_app = FastAPI(
                title=self.settings.title,
                docs_url="/docs" if self.settings.docs_enabled else None,
                redoc_url="/redoc" if self.settings.docs_enabled else None,
                openapi_url="/openapi.json" if self.settings.docs_enabled else None,
            )

        if not self.api_app:
            raise Exception("API App could not be created.")

        if not self.router:
            self.router = APIRouter(prefix="/v1")

        if not self.router:
            raise Exception("API Router could not be created.")

        self.router.include_router(self.get_router())
        self.api_app.include_router(self.router)

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

        _host = host or "localhost"
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
