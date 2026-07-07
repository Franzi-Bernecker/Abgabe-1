"""SQLite-Verbindung und Schema-Initialisierung."""

import sqlite3

from cardioconnect.config import get_db_path

_SCHEMA = """
    CREATE TABLE IF NOT EXISTS persons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        firstname TEXT NOT NULL,
        lastname TEXT NOT NULL,
        date_of_birth TEXT NOT NULL,
        gender TEXT NOT NULL DEFAULT 'male',
        picture_path TEXT NOT NULL DEFAULT 'data/pictures/none.jpg',
        height_cm REAL,
        weight_kg REAL,
        body_fat_pct REAL
    );

    CREATE TABLE IF NOT EXISTS ekg_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        file_path TEXT NOT NULL,
        FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'running',
        name TEXT NOT NULL DEFAULT '',
        file_path TEXT NOT NULL,
        FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'patient',
        person_id INTEGER UNIQUE,
        FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
    );
"""


def get_connection() -> sqlite3.Connection:
    """Open a connection with dict-like rows and enforced foreign keys."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they do not exist yet."""
    get_db_path().parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(_SCHEMA)
