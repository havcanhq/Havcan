"""Password and token primitives used by the authentication service."""

import base64
import hashlib
import hmac
import secrets


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """Hash a password with a unique salt using PBKDF2-HMAC-SHA256."""

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    return f"${PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${encode(salt)}${encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password without revealing whether the hash matched early."""

    try:
        _, scheme, iterations, encoded_salt, encoded_digest = stored_hash.split("$")
        if scheme != PASSWORD_SCHEME:
            return False
        salt = base64.urlsafe_b64decode(encoded_salt + "=" * (-len(encoded_salt) % 4))
        expected = base64.urlsafe_b64decode(encoded_digest + "=" * (-len(encoded_digest) % 4))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def create_token() -> str:
    """Create an opaque token suitable for a session or reset link."""

    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash an opaque token before storing it in MongoDB."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()