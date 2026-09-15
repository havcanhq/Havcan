"""HTTP API for registration, login, sessions, and password recovery."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError

from .dependencies import get_auth_repository, get_current_user, require_roles
from .repository import AuthRepository, expires_in
from .schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    PublicUser,
    RegisterRequest,
    ResetPasswordRequest,
)
from .security import create_token, hash_password, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


def serialize_user(user: dict[str, Any]) -> PublicUser:
    """Remove Mongo's internal id and password fields from API responses."""

    return PublicUser(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        role=user["role"],
        profile_image=user.get("profile_image"),
        is_active=user["is_active"],
        email_verified=user["email_verified"],
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    settings = request.app.state.settings
    secure_cookie = settings.auth_cookie_secure or settings.app_env == "production"
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response, request: Request) -> None:
    settings = request.app.state.settings
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure or settings.app_env == "production",
        samesite="lax",
        path="/",
    )


async def create_session(
    request: Request,
    response: Response,
    repository: AuthRepository,
    user_id: str,
) -> None:
    token = create_token()
    await repository.create_session(
        token,
        user_id,
        expires_in(request.app.state.settings.session_ttl_seconds),
    )
    set_session_cookie(response, request, token)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    repository: AuthRepository = Depends(get_auth_repository),
) -> dict[str, Any]:
    """Register a public client account; role is always assigned server-side."""

    if await repository.find_user_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    now = datetime.now(UTC)
    user = {
        "_id": uuid4().hex,
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": "CLIENT",
        "profile_image": None,
        "is_active": True,
        "email_verified": False,
        "created_at": now,
        "updated_at": now,
    }
    try:
        await repository.create_user(user)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from None
    await create_session(request, response, repository, user["_id"])
    return {"user": serialize_user(user).model_dump(mode="json")}


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    repository: AuthRepository = Depends(get_auth_repository),
) -> dict[str, Any]:
    user = await repository.find_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive")
    await create_session(request, response, repository, user["_id"])
    return {"user": serialize_user(user).model_dump(mode="json")}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    repository: AuthRepository = Depends(get_auth_repository),
) -> dict[str, str]:
    token = request.cookies.get(request.app.state.settings.session_cookie_name)
    if token:
        await repository.delete_session(token)
    clear_session_cookie(response, request)
    return {"message": "Logged out successfully"}


@router.get("/me")
async def current_user(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return {"user": serialize_user(user).model_dump(mode="json")}


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    repository: AuthRepository = Depends(get_auth_repository),
) -> dict[str, str]:
    """Create a reset token without revealing whether an email exists.

    Email delivery is intentionally a later integration point. The token is
    stored hashed in MongoDB and can be delivered by the future mail service.
    """

    user = await repository.find_user_by_email(payload.email)
    if user is not None and user.get("is_active", False):
        await repository.create_password_reset(
            create_token(),
            user["_id"],
            expires_in(request.app.state.settings.password_reset_ttl_seconds),
        )
    return {"message": "If an account exists, password reset instructions will be sent shortly."}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    repository: AuthRepository = Depends(get_auth_repository),
) -> dict[str, str]:
    reset = await repository.consume_password_reset(payload.token)
    if reset is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = await repository.find_user_by_id(reset["user_id"])
    if user is None or not user.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    await repository.update_password(user["_id"], hash_password(payload.password), datetime.now(UTC))
    await repository.delete_user_sessions(user["_id"])
    return {"message": "Password reset successfully"}


@router.get("/protected")
async def protected_endpoint(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Small protected boundary used by clients and auth integration tests."""

    return {"user_id": str(user["_id"]), "role": user["role"]}


@router.get("/admin")
async def admin_endpoint(
    user: dict[str, Any] = Depends(require_roles("ADMIN")),
) -> dict[str, Any]:
    """Example of server-side role protection for future admin modules."""

    return {"user_id": str(user["_id"]), "role": user["role"]}