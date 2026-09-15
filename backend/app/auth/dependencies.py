"""FastAPI dependencies for authentication and server-side role protection."""

from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status

from .repository import AuthRepository, is_expired


async def get_auth_repository(request: Request) -> AuthRepository:
    """Resolve the repository only when an endpoint actually needs MongoDB."""

    database = request.app.state.mongo.database
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is not configured",
        )
    repository = AuthRepository(database)
    if not getattr(request.app.state, "auth_indexes_ready", False):
        try:
            await repository.ensure_indexes()
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication database is unavailable",
            ) from error
        request.app.state.auth_indexes_ready = True
    return repository


async def get_current_user(
    request: Request,
    repository: AuthRepository = Depends(get_auth_repository),
) -> dict[str, Any]:
    """Resolve the active user from the opaque, HTTP-only session cookie."""

    session_token = request.cookies.get(request.app.state.settings.session_cookie_name)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    session = await repository.find_session(session_token)
    if session is None or is_expired(session.get("expires_at")):
        await repository.delete_session(session_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user = await repository.find_user_by_id(session["user_id"])
    if user is None or not user.get("is_active", False):
        await repository.delete_session(session_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def require_roles(*roles: str) -> Callable[..., Any]:
    """Build a dependency that enforces roles on the server, never the client."""

    async def role_guard(
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return user

    return role_guard