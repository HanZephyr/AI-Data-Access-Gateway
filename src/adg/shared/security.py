import hashlib
import hmac
import secrets


def generate_api_key() -> str:
    return f"adg_{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    candidate = hash_api_key(raw_key)
    return hmac.compare_digest(candidate, hashed_key)
