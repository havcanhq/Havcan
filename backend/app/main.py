"""HAVCAN FastAPI application foundation."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.routes import router as auth_router
from .core.config import Settings, get_settings
from .db.mongo import MongoAdapter


def create_app(
    settings: Settings | None = None,
    mongo_adapter: MongoAdapter | None = None,
) -> FastAPI:
    """Build the API application with explicit, testable dependencies."""

    resolved_settings = settings or get_settings()
    mongo = mongo_adapter or MongoAdapter(resolved_settings.mongo_uri, resolved_settings.mongo_database)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await mongo.connect()
        try:
            yield
        finally:
            await mongo.close()

    application = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.mongo = mongo
    application.state.auth_indexes_ready = False
    application.include_router(auth_router)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health", tags=["system"])
    async def health() -> dict[str, object]:
        """Return a lightweight liveness/readiness foundation response."""

        database = "not_configured"
        if mongo.configured:
            database = "connected" if await mongo.ping() else "unavailable"
        return {
            "status": "ok",
            "service": resolved_settings.app_name,
            "version": application.version,
            "environment": resolved_settings.app_env,
            "database": database,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return application


app = create_app()