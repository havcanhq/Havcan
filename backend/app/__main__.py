"""Run the HAVCAN API with ``python -m backend.app``."""

import uvicorn

from .core.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "development",
    )