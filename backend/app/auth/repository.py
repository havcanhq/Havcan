"""MongoDB persistence boundary for users, sessions, and reset tokens."""

from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo.errors import DuplicateKeyError

from .security import hash_token


def is_expired(value: datetime | None) -> bool:
    """Compare both PyMongo naive UTC and timezone-aware datetimes safely."""

    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= datetime.now(UTC)


class AuthRepository:
    """Keep authentication persistence independent from the HTTP layer."""

    def __init__(self, database: Any) -> None:
        self.database = database

    @property
    def users(self) -> Any:
        return self.database["users"]

    @property
    def sessions(self) -> Any:
        return self.database["sessions"]

    @property
    def password_resets(self) -> Any:
        return self.database["password_resets"]

    async def ensure_indexes(self) -> None:
        """Create indexes lazily, so health works without a Mongo server."""

        await self.users.create_index("email", unique=True)
        await self.sessions.create_index("expires_at", expireAfterSeconds=0)
        await self.password_resets.create_index("expires_at", expireAfterSeconds=0)

    async def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.users.find_one({"email": email})

    async def find_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        return await self.users.find_one({"_id": user_id})

    async def create_user(self, user: dict[str, Any]) -> dict[str, Any]:
        try:
            await self.users.insert_one(user)
        except DuplicateKeyError:
            raise
        return user

    async def create_session(
        self,
        token: str,
        user_id: str,
        expires_at: datetime,
    ) -> None:
        await self.sessions.insert_one({
            "_id": hash_token(token),
            "user_id": user_id,
            "expires_at": expires_at,
            "created_at": datetime.now(UTC),
        })

    async def find_session(self, token: str) -> dict[str, Any] | None:
        return await self.sessions.find_one({"_id": hash_token(token)})

    async def delete_session(self, token: str) -> None:
        await self.sessions.delete_one({"_id": hash_token(token)})

    async def delete_user_sessions(self, user_id: str) -> None:
        await self.sessions.delete_many({"user_id": user_id})

    async def create_password_reset(
        self,
        token: str,
        user_id: str,
        expires_at: datetime,
    ) -> None:
        await self.password_resets.insert_one({
            "_id": hash_token(token),
            "user_id": user_id,
            "expires_at": expires_at,
            "created_at": datetime.now(UTC),
        })

    async def consume_password_reset(self, token: str) -> dict[str, Any] | None:
        token_hash = hash_token(token)
        reset = await self.password_resets.find_one({"_id": token_hash})
        if reset is None:
            return None
        if is_expired(reset.get("expires_at")):
            await self.password_resets.delete_one({"_id": token_hash})
            return None
        await self.password_resets.delete_one({"_id": token_hash})
        return reset

    async def update_password(
        self,
        user_id: str,
        password_hash: str,
        updated_at: datetime,
    ) -> None:
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"password_hash": password_hash, "updated_at": updated_at}},
        )


def expires_in(seconds: int) -> datetime:
    """Return a timezone-aware expiry timestamp."""

    return datetime.now(UTC) + timedelta(seconds=seconds)