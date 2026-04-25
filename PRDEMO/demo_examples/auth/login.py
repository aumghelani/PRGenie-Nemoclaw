"""
Demo PR: Rewrite login flow to use new JWT scheme.

Should trigger PRGenie HIGH RISK label because it touches auth/.
"""
import hashlib
import secrets


def hash_password(plain: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + plain).encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(plain: str, stored: str) -> bool:
    salt, h = stored.split("$", 1)
    return hashlib.sha256((salt + plain).encode()).hexdigest() == h


def make_session_token(user_id: int) -> str:
    return secrets.token_urlsafe(32)
