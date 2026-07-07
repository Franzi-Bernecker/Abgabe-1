"""Repository für Patienten-Stammdaten inkl. Profilbild-Upload."""

import io
from pathlib import Path

from PIL import Image

from cardioconnect.config import BASE_DIR, PICTURES_DIR
from cardioconnect.db import get_connection


def get_all() -> list[dict]:
    """All persons ordered by last name."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM persons ORDER BY lastname").fetchall()
    return [dict(r) for r in rows]


def get_by_id(person_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM persons WHERE id = ?", (person_id,)
        ).fetchone()
    return dict(row) if row else None


def create(
    firstname: str,
    lastname: str,
    date_of_birth: str,
    gender: str = "male",
    picture_path: str = "data/pictures/none.jpg",
    height_cm: float | None = None,
    weight_kg: float | None = None,
    body_fat_pct: float | None = None,
) -> int:
    """Insert a person and return the new id. Dates are ISO strings."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO persons (firstname, lastname, date_of_birth, gender, "
            "picture_path, height_cm, weight_kg, body_fat_pct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (firstname, lastname, date_of_birth, gender, picture_path,
             height_cm, weight_kg, body_fat_pct),
        )
        return cur.lastrowid


def update(
    person_id: int,
    firstname: str,
    lastname: str,
    date_of_birth: str,
    gender: str,
    picture_path: str | None = None,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    body_fat_pct: float | None = None,
) -> None:
    """Update master data; the picture is only replaced when a path is given."""
    with get_connection() as conn:
        if picture_path is not None:
            conn.execute(
                "UPDATE persons SET firstname=?, lastname=?, date_of_birth=?, "
                "gender=?, picture_path=?, height_cm=?, weight_kg=?, "
                "body_fat_pct=? WHERE id=?",
                (firstname, lastname, date_of_birth, gender, picture_path,
                 height_cm, weight_kg, body_fat_pct, person_id),
            )
        else:
            conn.execute(
                "UPDATE persons SET firstname=?, lastname=?, date_of_birth=?, "
                "gender=?, height_cm=?, weight_kg=?, body_fat_pct=? WHERE id=?",
                (firstname, lastname, date_of_birth, gender,
                 height_cm, weight_kg, body_fat_pct, person_id),
            )


def delete(person_id: int) -> None:
    """Delete a person; EKG tests, activities and accounts cascade via FK."""
    with get_connection() as conn:
        conn.execute("DELETE FROM persons WHERE id = ?", (person_id,))


def count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]


# ── Profilbild-Upload ──

def validate_picture_bytes(content: bytes) -> str | None:
    """Check that the bytes are a readable image. Returns an error or None."""
    try:
        Image.open(io.BytesIO(content)).verify()
        return None
    except Exception:
        return "Datei ist kein gültiges Bild (JPG/PNG erwartet)."


def crop_square(img: Image.Image) -> Image.Image:
    """Center-crop a picture to a square, biased toward the top (face area)."""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * 0.15)
    return img.crop((left, top, left + side, top + side))


def save_uploaded_picture(content: bytes, filename: str, person_id: int) -> str:
    """Store a profile picture (square-cropped) and return the repo-relative path."""
    PICTURES_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() or ".jpg"
    dest = PICTURES_DIR / f"P{person_id}{ext}"
    img = crop_square(Image.open(io.BytesIO(content)))
    if ext in (".jpg", ".jpeg") and img.mode != "RGB":
        img = img.convert("RGB")
    img.save(dest)
    return str(dest.relative_to(BASE_DIR)).replace("\\", "/")
