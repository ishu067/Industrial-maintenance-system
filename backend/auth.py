from __future__ import annotations

import hashlib
import hmac
import secrets

from backend.db import connect, row


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    actual = _hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


def register(full_name: str, email: str, password: str) -> dict:
    email = email.strip().lower()
    if row("SELECT id FROM users WHERE email = ?", (email,)):
        raise ValueError("Email already registered")
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO users(full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name.strip(), email, _hash_password(password)),
        )
    return {"user_id": cursor.lastrowid, "full_name": full_name.strip(), "email": email, "role": "operator"}


def login(email: str, password: str) -> dict | None:
    user = row("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    if not user or not _verify_password(password, user["password_hash"]):
        return None
    token = secrets.token_urlsafe(32)
    return {"access_token": token, "token_type": "bearer", "user_id": user["id"], "full_name": user["full_name"], "email": user["email"], "role": user["role"]}