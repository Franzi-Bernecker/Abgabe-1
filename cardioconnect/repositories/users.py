"""Repository für Benutzerkonten."""

import sqlite3

from cardioconnect.db import get_connection


def create_user(
    username: str,
    password_hash: str,
    salt: str,
    role: str = "patient",
    person_id: int | None = None,
) -> bool:
    """Insert a new user. Returns False if the username already exists."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role, person_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, salt, role, person_id),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_by_username(username: str) -> dict | None:
    """Return the user row as dict, or None if unknown."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None


def count_users() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
