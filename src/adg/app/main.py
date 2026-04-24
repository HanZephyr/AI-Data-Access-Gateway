from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from adg.admin_api.console import router as admin_console_router
from adg.admin_api.datasources import router as admin_datasource_router
from adg.admin_api.system import router as admin_system_router
from adg.app.settings import get_settings
from adg.control_plane.migrations.runtime import ensure_control_plane_schema
from adg.internal_api.decrypt import router as internal_decrypt_router
from adg.mcp_api.tools import router as mcp_tools_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Run startup migrations before the application begins serving requests."""

    settings = get_settings()
    ensure_control_plane_schema(settings.control_plane_database_url)
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application and attach all V1 routers."""

    settings = get_settings()
    app = FastAPI(title=settings.service_name, lifespan=lifespan)
    app.include_router(admin_console_router)
    app.include_router(admin_datasource_router)
    app.include_router(admin_system_router)
    app.include_router(internal_decrypt_router)
    app.include_router(mcp_tools_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Return a lightweight liveness response."""

        return {"status": "ok", "service": settings.service_name}

    @app.get("/ready", tags=["system"])
    def ready() -> dict[str, str]:
        """Return readiness for the current single-process service."""

        return {"status": "ready"}

    return app


def run() -> None:
    """Run the local development server entry point."""

    uvicorn.run("adg.app.main:create_app", factory=True, host="127.0.0.1", port=8000)
