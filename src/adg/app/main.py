import uvicorn
from fastapi import FastAPI

from adg.admin_api.console import router as admin_console_router
from adg.admin_api.datasources import router as admin_datasource_router
from adg.admin_api.system import router as admin_system_router
from adg.app.settings import get_settings
from adg.internal_api.decrypt import router as internal_decrypt_router
from adg.mcp_api.tools import router as mcp_tools_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.service_name)
    app.include_router(admin_console_router)
    app.include_router(admin_datasource_router)
    app.include_router(admin_system_router)
    app.include_router(internal_decrypt_router)
    app.include_router(mcp_tools_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    @app.get("/ready", tags=["system"])
    def ready() -> dict[str, str]:
        return {"status": "ready"}

    return app


def run() -> None:
    uvicorn.run("adg.app.main:create_app", factory=True, host="127.0.0.1", port=8000)
