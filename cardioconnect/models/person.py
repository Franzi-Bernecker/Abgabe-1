"""Patient als Domänen-Objekt mit abgeleiteten Kennzahlen."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cardioconnect.config import BASE_DIR, FALLBACK_PICTURE


@dataclass(frozen=True)
class Person:
    """A patient as stored in the ``persons`` table."""

    id: int
    firstname: str
    lastname: str
    date_of_birth: str  # ISO: YYYY-MM-DD
    gender: str  # "male" | "female"
    picture_path: str
    height_cm: float | None = None
    weight_kg: float | None = None
    body_fat_pct: float | None = None

    @classmethod
    def from_row(cls, row: dict) -> "Person":
        """Build a Person from a DB row dict (ignores unknown keys)."""
        fields = {k: row[k] for k in cls.__dataclass_fields__ if k in row}
        return cls(**fields)

    # ── Abgeleitete Werte ──

    @property
    def full_name(self) -> str:
        return f"{self.firstname} {self.lastname}"

    @property
    def birth_date(self) -> date | None:
        try:
            return date.fromisoformat(self.date_of_birth)
        except (TypeError, ValueError):
            return None

    @property
    def age(self) -> int:
        """Age in full years; 0 if the birth date is unparsable."""
        born = self.birth_date
        if born is None:
            return 0
        today = date.today()
        return today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )

    @property
    def max_heart_rate(self) -> int:
        """Theoretical maximum heart rate (220 − age)."""
        return 220 - self.age

    @property
    def bmi(self) -> float | None:
        if self.height_cm and self.weight_kg:
            return round(self.weight_kg / (self.height_cm / 100) ** 2, 1)
        return None

    @property
    def picture_file(self) -> Path:
        """Absolute path to the profile picture, falling back to a placeholder."""
        path = BASE_DIR / self.picture_path
        return path if path.exists() else FALLBACK_PICTURE

    # ── Anzeige ──

    @property
    def gender_label(self) -> str:
        return "Männlich" if self.gender == "male" else "Weiblich"

    def format_birth_date(self) -> str:
        born = self.birth_date
        return born.strftime("%d.%m.%Y") if born else "–"
