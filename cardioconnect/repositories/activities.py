"""Repository für Trainings-Aktivitäten (GPX) inkl. Upload mit Validierung."""

import io

import gpxpy

from cardioconnect.config import BASE_DIR, GPX_DIR
from cardioconnect.db import get_connection


def get_for_person(person_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM activities WHERE person_id = ? ORDER BY date",
            (person_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(activity_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM activities WHERE id = ?", (activity_id,)
        ).fetchone()
    return dict(row) if row else None


def create(person_id: int, date_iso: str, activity_type: str,
           name: str, file_path: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO activities (person_id, date, type, name, file_path) "
            "VALUES (?, ?, ?, ?, ?)",
            (person_id, date_iso, activity_type, name, file_path),
        )
        return cur.lastrowid


def delete(activity_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))


def count_for_person(person_id: int) -> int:
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM activities WHERE person_id = ?", (person_id,)
        ).fetchone()[0]


# ── Upload ──

def parse_gpx_metadata(content: bytes) -> dict | None:
    """Parse GPX bytes; return {name, type, date} or None if invalid/empty.

    A track needs at least two points to be usable for map and statistics.
    """
    try:
        gpx = gpxpy.parse(io.BytesIO(content))
    except Exception:
        return None

    points = [p for trk in gpx.tracks for seg in trk.segments for p in seg.points]
    if len(points) < 2:
        return None

    track = gpx.tracks[0]
    start_time = points[0].time
    return {
        "name": track.name or "Aktivität",
        "type": track.type or "running",
        "date": start_time.date().isoformat() if start_time else "",
    }


def save_uploaded_gpx(content: bytes, person_id: int) -> str:
    """Store GPX bytes and return the repo-relative path."""
    GPX_DIR.mkdir(parents=True, exist_ok=True)
    # Nächsten freien Index wählen — nach Löschungen könnte der Zähler sonst
    # die Datei einer noch referenzierten Aktivität überschreiben.
    idx = count_for_person(person_id) + 1
    while (GPX_DIR / f"P{person_id}_{idx}.gpx").exists():
        idx += 1
    dest = GPX_DIR / f"P{person_id}_{idx}.gpx"
    dest.write_bytes(content)
    return str(dest.relative_to(BASE_DIR)).replace("\\", "/")
