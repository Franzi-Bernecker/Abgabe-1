"""GPX-Aktivitäten: Parsen, Track-Punkte, Herzfrequenz und Trainings-Kennzahlen."""

from dataclasses import dataclass

import gpxpy
import numpy as np
import pandas as pd
import streamlit as st

from cardioconnect.config import BASE_DIR

#: Deutsche Labels für die Aktivitätstypen aus den Strava-GPX-Dateien.
ACTIVITY_TYPE_LABELS = {
    "running": "Lauf",
    "cycling": "Radtour",
    "hiking": "Wanderung",
    "walking": "Spaziergang",
}

#: Untergrenzen der HR-Trainingszonen als Anteil der maximalen Herzfrequenz.
_ZONE_BOUNDS = [
    ("Z1 Regeneration", 0.00),
    ("Z2 Grundlage", 0.60),
    ("Z3 Aerob", 0.70),
    ("Z4 Schwelle", 0.80),
    ("Z5 Maximal", 0.90),
]

#: Angenommene maximale Herzfrequenz, falls kein Patientenalter vorliegt.
DEFAULT_MAX_HR = 190


def _extract_hr(point) -> float:
    """Read the heart rate from a trackpoint's Garmin TrackPointExtension."""
    for extension in point.extensions:
        for element in extension.iter():
            if element.tag.rsplit("}", 1)[-1] == "hr" and element.text:
                try:
                    return float(element.text)
                except ValueError:
                    return np.nan
    return np.nan


@st.cache_data(show_spinner="GPX-Track wird geladen …")
def load_track(file_path: str) -> dict:
    """Parse a GPX file into track points and summary statistics.

    Returns a dict with:
    - ``points``: DataFrame(lat, lon, ele_m, dist_m, hr) — dist_m cumulative,
      hr is NaN where the track carries no heart-rate data
    - ``distance_km``, ``duration_s``, ``elevation_gain_m``, ``avg_speed_kmh``
    - ``has_hr``: whether any trackpoint carries heart-rate data
    """
    with open(BASE_DIR / file_path, encoding="utf-8") as fh:
        gpx = gpxpy.parse(fh)

    rows = []
    dist_m = 0.0
    prev = None
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if prev is not None:
                    dist_m += point.distance_3d(prev) or 0.0
                rows.append({
                    "lat": point.latitude,
                    "lon": point.longitude,
                    "ele_m": point.elevation,
                    "dist_m": dist_m,
                    "hr": _extract_hr(point),
                })
                prev = point

    points = pd.DataFrame(rows)
    duration_s = gpx.get_duration() or 0.0
    uphill, _ = gpx.get_uphill_downhill()
    distance_km = dist_m / 1000.0

    return {
        "points": points,
        "distance_km": round(distance_km, 2),
        "duration_s": duration_s,
        "elevation_gain_m": round(uphill or 0.0),
        "avg_speed_kmh": round(distance_km / (duration_s / 3600), 1)
        if duration_s > 0 else 0.0,
        "has_hr": bool(points["hr"].notna().any()),
    }


@dataclass(frozen=True)
class Activity:
    """An activity (row from ``activities``) backed by a GPX file."""

    id: int
    person_id: int
    date: str  # ISO
    type: str
    name: str
    file_path: str

    @classmethod
    def from_row(cls, row: dict) -> "Activity":
        fields = {k: row[k] for k in cls.__dataclass_fields__ if k in row}
        return cls(**fields)

    @property
    def track(self) -> dict:
        return load_track(self.file_path)

    @property
    def has_hr(self) -> bool:
        return self.track["has_hr"]

    @property
    def type_label(self) -> str:
        return ACTIVITY_TYPE_LABELS.get(self.type, self.type.capitalize())

    @property
    def avg_pace_min_km(self) -> float | None:
        """Average pace in min/km, or None for zero-distance tracks."""
        stats = self.track
        if stats["distance_km"] <= 0 or stats["duration_s"] <= 0:
            return None
        return (stats["duration_s"] / 60.0) / stats["distance_km"]

    # ── Herzfrequenz ──

    def hr_stats(self) -> dict | None:
        """Mean/min/max heart rate in bpm, or None if the track has no HR."""
        hr = self.track["points"]["hr"].dropna()
        if hr.empty:
            return None
        return {
            "mean": int(round(hr.mean())),
            "min": int(hr.min()),
            "max": int(hr.max()),
        }

    def hr_zones(self, max_hr: int = DEFAULT_MAX_HR) -> pd.DataFrame | None:
        """Share of trackpoints in each HR training zone (percent of time)."""
        hr = self.track["points"]["hr"].dropna().to_numpy()
        if len(hr) == 0:
            return None
        labels = [name for name, _ in _ZONE_BOUNDS]
        lowers = [frac * max_hr for _, frac in _ZONE_BOUNDS]
        uppers = lowers[1:] + [10_000.0]
        rows = []
        for label, lo, hi in zip(labels, lowers, uppers):
            pct = 100 * np.mean((hr >= lo) & (hr < hi))
            rows.append({"zone": label, "pct": round(float(pct), 1)})
        return pd.DataFrame(rows)

    # ── Trainings-Tipps ──

    def tips(self, max_hr: int = DEFAULT_MAX_HR) -> list[str]:
        """Rule-based training hints (automated, not medical advice)."""
        stats = self.track
        notes: list[str] = []

        hr = self.hr_stats()
        if hr is not None:
            intensity = hr["mean"] / max_hr
            if intensity >= 0.85:
                notes.append(
                    f"Intensive Einheit (Ø {hr['mean']} bpm ≈ "
                    f"{intensity:.0%} der Max-HR) — nächste Einheit locker "
                    "als Regenerationslauf gestalten."
                )
            elif intensity <= 0.7:
                notes.append(
                    f"Ruhige Einheit (Ø {hr['mean']} bpm ≈ {intensity:.0%} "
                    "der Max-HR) — gute Grundlage; für Fortschritt gelegentlich "
                    "ein Tempo- oder Intervalltraining ergänzen."
                )
            else:
                notes.append(
                    f"Moderate Einheit (Ø {hr['mean']} bpm ≈ {intensity:.0%} "
                    "der Max-HR) — solides Dauerlauf-Tempo."
                )
            if hr["max"] >= 0.95 * max_hr:
                notes.append(
                    f"Spitzen-HR {hr['max']} bpm nahe am Maximum — auf "
                    "ausreichende Erholung achten."
                )
        else:
            notes.append(
                "Keine Herzfrequenzdaten in diesem Track — für aussagekräftige "
                "Trainingssteuerung einen Brustgurt/Uhr mit HR nutzen."
            )

        if stats["elevation_gain_m"] >= 300:
            notes.append(
                f"Anspruchsvolles Höhenprofil (+{stats['elevation_gain_m']} m) — "
                "Regeneration entsprechend einplanen."
            )
        return notes

    # ── Anzeige ──

    def format_pace(self) -> str:
        pace = self.avg_pace_min_km
        if pace is None:
            return "–"
        minutes, seconds = divmod(round(pace * 60), 60)
        return f"{minutes}:{seconds:02d} min/km"

    def format_duration(self) -> str:
        total = int(self.track["duration_s"])
        hours, rest = divmod(total, 3600)
        minutes, seconds = divmod(rest, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d} h"
        return f"{minutes}:{seconds:02d} min"

    def format_date(self) -> str:
        try:
            return pd.Timestamp(self.date).strftime("%d.%m.%Y")
        except ValueError:
            return self.date
