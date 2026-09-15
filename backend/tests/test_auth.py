"""Focused authentication and authorization tests."""

from datetime import UTC, datetime, timedelta
import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.security import hash_password, verify_password
from backend.app.auth.repository import AuthRepository
from backend.app.auth.security import create_token
from backend.app.core.config import Settings
from backend.app.main import create_app


class FakeCollection:
    def __init__(self) -> None:
        self.documents: dict[Any, dict[str, Any]] = {}
        self.indexes: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def create_index(self, *fields: Any, **options: Any) -> None:
        self.indexes.append((fields, options))

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for document in self.documents.values():
            if all(document.get(key) == value for key, value in query.items()):
                return dict(document)
        return None

    async def insert_one(self, document: dict[str, Any]) -> None:
        if "_id" in document and document["_id"] in self.documents:
            from pymongo.errors import DuplicateKeyError

            raise DuplicateKeyError("duplicate _id")
        if "email" in document and any(item.get("email") == document["email"] for item in self.documents.values()):
            from pymongo.errors import DuplicateKeyError

            raise DuplicateKeyError("duplicate email")
        self.documents[document["_id"]] = dict(document)

    async def delete_one(self, query: dict[str, Any]) -> None:
        document = await self.find_one(query)
        if document:
            self.documents.pop(document["_id"], None)

    async def delete_many(self, query: dict[str, Any]) -> None:
        matching = [
            key for key, document in self.documents.items()
            if all(document.get(field) == value for field, value in query.items())
        ]
        for key in matching:
            self.documents.pop(key, None)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        document = await self.find_one(query)
        if document:
            document.update(update.get("$set", {}))
            self.documents[document["_id"]] = document


class FakeDatabase:
    def __init__(self) -> None:
        self.collections = {
            "users": FakeCollection(),
            "sessions": FakeCollection(),
            "password_resets": FakeCollection(),
        }

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections[name]


class FakeMongo:
    def __init__(self) -> None:
        self.database = FakeDatabase()

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass


@pytest.fixture()
def client() -> TestClient:
    app = create_app(
        Settings(mongo_uri="mongodb://test", auth_cookie_secure=False),
        mongo_adapter=FakeMongo(),  # type: ignore[arg-type]
    )
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, email: str = "client@example.com") -> dict[str, Any]:
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Aarav Client",
            "email": email,
            "password": "correct horse battery",
            "confirm_password": "correct horse battery",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_registration_creates_client_and_hashes_password(client: TestClient) -> None:
    payload = register(client)
    user = payload["user"]

    assert user["role"] == "CLIENT"
    assert user["email"] == "client@example.com"
    assert "password_hash" not in user
    assert client.cookies.get("havcan_session")


def test_duplicate_email_is_rejected(client: TestClient) -> None:
    register(client)
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Another Client",
            "email": "CLIENT@example.com",
            "password": "correct horse battery",
            "confirm_password": "correct horse battery",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email is already registered"


def test_login_and_invalid_password(client: TestClient) -> None:
    register(client)
    client.post("/api/auth/logout")

    response = client.post(
        "/api/auth/login",
        json={"email": "client@example.com", "password": "wrong password"},
    )
    assert response.status_code == 401

    response = client.post(
        "/api/auth/login",
        json={"email": "CLIENT@example.com", "password": "correct horse battery"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "CLIENT"


def test_logout_and_current_authenticated_user(client: TestClient) -> None:
    register(client)
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["name"] == "Aarav Client"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_protected_and_role_protected_routes(client: TestClient) -> None:
    assert client.get("/api/auth/protected").status_code == 401
    register(client)
    assert client.get("/api/auth/protected").status_code == 200
    assert client.get("/api/auth/admin").status_code == 403


def test_password_hashing_is_salted_and_verifiable() -> None:
    first = hash_password("correct horse battery")
    second = hash_password("correct horse battery")

    assert first != second
    assert verify_password("correct horse battery", first)
    assert not verify_password("wrong password", first)
    assert first.startswith("$pbkdf2_sha256$600000$")


def test_forgot_and_reset_password_foundation(client: TestClient) -> None:
    register(client)
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "client@example.com"},
    )
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]

    # A real mail integration will deliver the raw token. The test obtains it
    # from the fake persistence boundary without exposing it through the API.
    app = client.app
    database = app.state.mongo.database
    reset_document = next(iter(database["password_resets"].documents.values()))
    assert reset_document["expires_at"] > datetime.now(UTC) - timedelta(seconds=1)

    user_id = next(iter(database["users"].documents.values()))["_id"]
    raw_token = create_token()
    asyncio.run(
        AuthRepository(database).create_password_reset(
            raw_token,
            user_id,
            datetime.now(UTC) + timedelta(minutes=5),
        ),
    )
    reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": raw_token,
            "password": "new correct password",
            "confirm_password": "new correct password",
        },
    )
    assert reset.status_code == 200
    client.cookies.clear()
    login = client.post(
        "/api/auth/login",
        json={"email": "client@example.com", "password": "new correct password"},
    )
    assert login.status_code == 200