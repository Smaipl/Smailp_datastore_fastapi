import hashlib
import os

TOKEN_PEPPER = os.getenv("TOKEN_PEPPER", "please-change-me")


def hash_token(token: str) -> str:
    return hashlib.sha256((token + TOKEN_PEPPER).encode("utf-8")).hexdigest()
