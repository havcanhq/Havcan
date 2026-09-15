"""Small MongoDB adapter boundary for future repositories.

The adapter is intentionally lazy: Phase 1 can run and expose health checks
without a MongoDB server, while later domains can depend on this boundary
instead of constructing clients throughout the application.
"""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class MongoAdapter:
    """Own the Mongo client lifecycle and expose a minimal database boundary."""

    def __init__(self, uri: str | None, database_name: str) -> None:
        self.uri = uri
        self.database_name = database_name
        self.client: AsyncIOMotorClient[Any] | None = None

    @property
    def configured(self) -> bool:
        """Whether a MongoDB URI has been provided."""

        return bool(self.uri)

    @property
    def database(self) -> AsyncIOMotorDatabase[Any] | None:
        """Return the configured database, if a client is connected."""

        if self.client is None:
            return None
        return self.client[self.database_name]

    async def connect(self) -> None:
        """Create a client without forcing a network connection at startup."""

        if self.uri and self.client is None:
            self.client = AsyncIOMotorClient(self.uri, serverSelectionTimeoutMS=1500)

    async def ping(self) -> bool:
        """Return whether MongoDB responds to a short ping."""

        if self.client is None:
            return False
        try:
            await self.client.admin.command("ping")
        except Exception:
            return False
        return True

    async def close(self) -> None:
        """Close the client when the API process shuts down."""

        if self.client is not None:
            self.client.close()
            self.client = None