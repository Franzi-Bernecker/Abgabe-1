"""Repository für EKG-Tests inkl. Datei-Upload mit Validierung."""

import io
from pathlib import Path

import pandas as pd

from cardioconnect.config import BASE_DIR, EKG_DIR
from cardioconnect.db import get_connection


def get_for_person(person_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM ekg_tests WHERE person_id = ? ORDER BY date",
            (person_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(test_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ekg_tests WHERE id = ?", (test_id,)
        ).fetchone()
    return dict(row) if row else None


def create(person_id: int, date_iso: str, file_path: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO ekg_tests (person_id, date, file_path) VALUES (?, ?, ?)",
            (person_id, date_iso, file_path),
        )
        return cur.lastrowid


def delete(test_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM ekg_tests WHERE id = ?", (test_id,))


def count_for_person(person_id: int) -> int:
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM ekg_tests WHERE person_id = ?", (person_id,)
        ).fetchone()[0]


# ── Upload ──

def normalize_ekg_text(content: bytes, filename: str) -> bytes:
    """Convert tab-separated .txt exports to comma-separated CSV bytes."""
    if not filename.lower().endswith(".txt"):
        return content
    text = content.decode("utf-8", errors="replace")
    first_line = text.split("\n", 1)[0]
    if "\t" in first_line:
        text = text.replace("\t", ",")
    return text.encode("utf-8")


def validate_ekg_bytes(content: bytes) -> str | None:
    """Check that the bytes parse as an EKG CSV. Returns an error message or None."""
    try:
        df = pd.read_csv(io.BytesIO(content), index_col=0, nrows=500)
    except Exception:
        return "Datei konnte nicht als CSV gelesen werden."
    numeric = df.select_dtypes("number")
    if numeric.empty:
        return "Datei enthält keine numerische Signalspalte."
    if len(df) < 100:
        return "Datei enthält zu wenige Messwerte für eine EKG-Analyse."
    return None


def save_uploaded_ekg(content: bytes, filename: str, person_id: int) -> str:
    """Store normalized EKG bytes and return the repo-relative path."""
    EKG_DIR.mkdir(parents=True, exist_ok=True)
    # Nächsten freien Index wählen — nach Löschungen könnte der Zähler sonst
    # den Dateinamen eines noch referenzierten Tests überschreiben.
    idx = count_for_person(person_id) + 1
    while (EKG_DIR / f"{person_id}P_{idx}_ekg.csv").exists():
        idx += 1
    dest = EKG_DIR / f"{person_id}P_{idx}_ekg.csv"
    dest.write_bytes(normalize_ekg_text(content, filename))

    # Drop a stale parquet side-cache if a file with this name existed before.
    parquet = dest.with_suffix(".parquet")
    parquet.unlink(missing_ok=True)

    return str(dest.relative_to(BASE_DIR)).replace("\\", "/")
