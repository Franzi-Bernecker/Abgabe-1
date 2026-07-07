"""Passwort-Hashing (PBKDF2) und Login-Session-Verwaltung."""

import hashlib
import hmac
import secrets

import streamlit as st

from cardioconnect.config import PBKDF2_ITERATIONS
from cardioconnect.repositories import users


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Derive a PBKDF2-SHA256 hash; returns (hex_hash, hex_salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def authenticate(username: str, password: str) -> dict | None:
    """Return the user dict on valid credentials, otherwise None."""
    user = users.get_by_username(username.strip())
    if user is None:
        return None
    if not verify_password(password, user["password_hash"], user["salt"]):
        return None
    return user


# ── Session ──

def current_user() -> dict | None:
    return st.session_state.get("user")


def login(user: dict) -> None:
    st.session_state["user"] = user


def logout() -> None:
    st.session_state.clear()


def is_doctor() -> bool:
    user = current_user()
    return user is not None and user["role"] == "doctor"
