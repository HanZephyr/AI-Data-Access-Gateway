import hashlib
import hmac
import secrets


def generate_api_key() -> str:
    """Generate a random API key with the ADG prefix used in examples."""

    return f"adg_{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    """Hash an API key before storing it in the control-plane database."""

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Compare a raw API key against a stored hash without timing leaks."""

    candidate = hash_api_key(raw_key)
    return hmac.compare_digest(candidate, hashed_key)
