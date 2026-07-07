"""Zentrale Konfiguration: Pfade, Konstanten und Zugriff auf Streamlit-Secrets."""

from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EKG_DIR = DATA_DIR / "ekg_data"
GPX_DIR = DATA_DIR / "gpx"
PICTURES_DIR = DATA_DIR / "pictures"

FALLBACK_PICTURE = PICTURES_DIR / "none.jpg"

#: Abtastrate der EKG-Aufnahmen (MIT-BIH-Format) in Hz.
EKG_SAMPLE_RATE = 360

#: Grenzwerte für Herzfrequenz-Klassifikation in bpm.
BRADYCARDIA_BPM = 60
TACHYCARDIA_BPM = 100

#: PBKDF2-Iterationen für Passwort-Hashing.
PBKDF2_ITERATIONS = 600_000

#: Erlaubte Dateiendungen für Uploads.
ALLOWED_EKG_EXTENSIONS = (".csv", ".txt")
ALLOWED_GPX_EXTENSIONS = (".gpx",)
ALLOWED_PICTURE_EXTENSIONS = (".jpg", ".jpeg", ".png")


def get_secret(section: str, key: str, default: str | None = None) -> str:
    """Read a value from ``st.secrets`` with a helpful error message.

    Args:
        section: Top-level section in ``secrets.toml`` (e.g. ``"auth"``).
        key: Key inside the section.
        default: Value returned when the key is missing. ``None`` means
            the key is required.

    Raises:
        RuntimeError: If a required secret is missing.
    """
    try:
        return str(st.secrets[section][key])
    except (KeyError, FileNotFoundError):
        if default is not None:
            return default
        raise RuntimeError(
            f"Secret [{section}] {key} fehlt. Bitte `.streamlit/secrets.toml` "
            "anhand von `secrets.toml.example` anlegen."
        ) from None


def get_db_path() -> Path:
    """Database location, overridable via ``[database] path`` in secrets."""
    override = get_secret("database", "path", default="")
    if override:
        return (BASE_DIR / override).resolve()
    return DATA_DIR / "cardioconnect.db"
