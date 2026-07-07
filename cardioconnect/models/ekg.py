"""EKG-Signalanalyse im Stil eines Holter-Befunds.

Die Rohdaten (MIT-BIH-Export, 360 Hz) werden beim ersten Laden in eine
Parquet-Datei umgewandelt und über ``st.cache_data`` im Speicher gehalten,
damit 650k-Punkte-Signale nicht bei jedem Rerun neu geparst werden.

Statt jeden einzelnen Herzschlag als „Auffälligkeit" zu melden, werden
aufeinanderfolgende auffällige Schläge zu **Episoden** zusammengefasst und als
klinische Kennzahlen (Pausen, Ektopie-Last, Zeit je Frequenzband) aufbereitet —
so wie ein echter Langzeit-EKG-Befund aufgebaut ist.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from scipy.signal import find_peaks

from cardioconnect.config import (
    BASE_DIR,
    BRADYCARDIA_BPM,
    EKG_SAMPLE_RATE,
    TACHYCARDIA_BPM,
)

#: Bekannte Signalspalten in MIT-BIH-Exporten, in Präferenz-Reihenfolge.
SIGNAL_COLUMNS = ("MLII", "V5", "V1", "V2")

#: Mindestabstand zweier R-Zacken (~210 bpm Obergrenze) in Sekunden.
_MIN_PEAK_DISTANCE_S = 0.28

#: Anteil der 5.–95.-Perzentil-Spannweite, den eine R-Zacke herausragen muss.
_PEAK_PROMINENCE_FRACTION = 0.4

#: Ein RR-Intervall länger als dieser Wert gilt als Pause (Sekunden).
_PAUSE_S = 2.0

#: Mindestdauer, ab der eine Tachy-/Bradykardie als Episode gilt (Sekunden).
_MIN_SUSTAINED_S = 10.0

#: Fenstergröße (Schläge) für die geglättete HR der Episoden-Erkennung.
_HR_SMOOTH_BEATS = 9

#: Ab so vielen aufeinanderfolgenden ektopen Schlägen wird ein Run gelistet.
_MIN_ECTOPIC_RUN = 2

#: Physiologisch plausibles HR-Band für Kennzahlen (bpm).
_HR_PLAUSIBLE = (35.0, 210.0)

#: Deutsche Labels und Reihenfolge der Auffälligkeitstypen.
ANOMALY_LABELS = {
    "pause": "Pause / Aussetzer",
    "irregular": "Irregulärer Schlag (Ektopie)",
    "tachycardia": "Tachykardie (>100 bpm)",
    "bradycardia": "Bradykardie (<60 bpm)",
}


def _resolve(file_path: str) -> Path:
    return BASE_DIR / file_path


def _csv_to_parquet(csv_path: Path) -> Path:
    """Maintain a Parquet side-cache next to the CSV; returns the Parquet path."""
    parquet_path = csv_path.with_suffix(".parquet")
    if (
        parquet_path.exists()
        and parquet_path.stat().st_mtime >= csv_path.stat().st_mtime
    ):
        return parquet_path

    df = pd.read_csv(csv_path, index_col=0)
    signal_col = next(
        (c for c in SIGNAL_COLUMNS if c in df.columns),
        df.select_dtypes("number").columns[0],
    )
    pd.DataFrame(
        {"signal": df[signal_col].astype("float32")}
    ).to_parquet(parquet_path, engine="pyarrow")
    return parquet_path


@st.cache_data(show_spinner="EKG-Daten werden geladen …")
def load_signal(file_path: str) -> pd.DataFrame:
    """Load an EKG file as DataFrame with columns ``time_s`` and ``signal``."""
    parquet_path = _csv_to_parquet(_resolve(file_path))
    df = pd.read_parquet(parquet_path, engine="pyarrow")
    df["time_s"] = np.arange(len(df)) / EKG_SAMPLE_RATE
    return df


def _find_r_peaks(signal: np.ndarray) -> np.ndarray:
    """Robust R-peak detection via prominence + refractory distance.

    Prominence (rather than a global height threshold) tolerates baseline
    wander, and the minimum distance enforces a physiological refractory
    period — together they suppress the false/missed beats that previously
    produced impossible heart rates.
    """
    p_low, p_high = np.percentile(signal, [5, 95])
    prominence = max(1e-3, _PEAK_PROMINENCE_FRACTION * (p_high - p_low))
    distance = int(_MIN_PEAK_DISTANCE_S * EKG_SAMPLE_RATE)
    peaks, _ = find_peaks(signal, distance=distance, prominence=prominence)
    return peaks


def _classify_beats(rr_s: np.ndarray) -> list[str | None]:
    """Label each RR interval; None means a normal beat.

    Robust statistics (median + MAD) drive the ectopic ("irregular") test so a
    few extreme intervals don't skew the threshold.
    """
    if len(rr_s) < 2:
        return [None] * len(rr_s)

    median_rr = float(np.median(rr_s))
    mad = float(np.median(np.abs(rr_s - median_rr)))
    mad_sigma = mad * 1.4826 if mad > 0 else float(np.std(rr_s, ddof=1))

    labels: list[str | None] = []
    for rr in rr_s:
        hr = 60.0 / rr if rr > 0 else 0.0
        deviation = abs(rr - median_rr)
        relative_dev = deviation / median_rr if median_rr > 0 else 0.0

        if rr > _PAUSE_S:
            labels.append("pause")
        elif mad_sigma > 0 and deviation > 3 * mad_sigma and relative_dev > 0.20:
            labels.append("irregular")
        elif hr > TACHYCARDIA_BPM:
            labels.append("tachycardia")
        elif hr < BRADYCARDIA_BPM:
            labels.append("bradycardia")
        else:
            labels.append(None)
    return labels


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Yield (start, end_inclusive) index ranges where ``mask`` is True."""
    ranges = []
    i = 0
    n = len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and mask[j + 1]:
            j += 1
        ranges.append((i, j))
        i = j + 1
    return ranges


def _episode(peak_times, rr_s, i, j, etype) -> dict:
    segment_rr = rr_s[i:j + 1]
    mean_hr = float(60.0 / np.mean(segment_rr)) if len(segment_rr) else 0.0
    return {
        "type": etype,
        "start_s": float(peak_times[i]),
        "end_s": float(peak_times[j + 1]),
        "duration_s": float(peak_times[j + 1] - peak_times[i]),
        "beat_count": int(j - i + 1),
        "mean_hr": round(mean_hr, 1),
        "max_rr_ms": round(float(np.max(segment_rr)) * 1000, 0),
    }


def _group_episodes(
    peak_times: np.ndarray, rr_s: np.ndarray, labels: list[str | None]
) -> list[dict]:
    """Build a curated event list — the way a Holter report reads.

    - **Pauses** (RR > 2 s): every one is listed individually.
    - **Ectopic runs**: only consecutive irregular beats of length ≥ 2
      (couplets / salvos); isolated single ectopics are captured by the
      burden metric instead of flooding the table.
    - **Sustained tachy-/bradycardia**: detected on a *smoothed* heart rate
      and only kept when the run lasts ≥ 10 s, so momentary fluctuations
      around the threshold don't fragment into thousands of one-beat events.
    """
    if len(rr_s) < 2:
        return []

    episodes: list[dict] = []
    labels_arr = np.array([lbl or "" for lbl in labels])

    # Pauses — each individually.
    for i, j in _runs(labels_arr == "pause"):
        episodes.append(_episode(peak_times, rr_s, i, j, "pause"))

    # Ectopic runs (≥ 2 consecutive irregular beats).
    for i, j in _runs(labels_arr == "irregular"):
        if j - i + 1 >= _MIN_ECTOPIC_RUN:
            episodes.append(_episode(peak_times, rr_s, i, j, "irregular"))

    # Sustained tachy/brady on smoothed HR.
    hr = 60.0 / np.where(rr_s > 0, rr_s, np.nan)
    hr_smooth = pd.Series(hr).rolling(
        _HR_SMOOTH_BEATS, center=True, min_periods=1
    ).median().to_numpy()
    for etype, mask in (
        ("tachycardia", hr_smooth > TACHYCARDIA_BPM),
        ("bradycardia", hr_smooth < BRADYCARDIA_BPM),
    ):
        for i, j in _runs(mask):
            duration = peak_times[j + 1] - peak_times[i]
            if duration >= _MIN_SUSTAINED_S:
                episodes.append(_episode(peak_times, rr_s, i, j, etype))

    episodes.sort(key=lambda ep: ep["start_s"])
    return episodes


@st.cache_data(show_spinner="EKG wird analysiert …")
def _analyze(file_path: str) -> dict:
    """Peaks, RR-Intervalle, Schlag-Klassifikation und Episoden (gecacht)."""
    signal = load_signal(file_path)["signal"].to_numpy()
    peaks = _find_r_peaks(signal)
    peak_times = peaks / EKG_SAMPLE_RATE
    rr_s = np.diff(peak_times)
    labels = _classify_beats(rr_s)

    return {
        "peaks": peaks,
        "peak_times_s": peak_times,
        "rr_s": rr_s,
        "labels": labels,
        "episodes": _group_episodes(peak_times, rr_s, labels),
    }


def analyze(file_path: str) -> dict:
    """Public accessor for the cached analysis (peaks, RR, labels, episodes)."""
    return _analyze(file_path)


@dataclass(frozen=True)
class EKG:
    """An EKG test (row from ``ekg_tests``) with lazy, cached analysis."""

    id: int
    person_id: int
    date: str  # ISO
    file_path: str

    @classmethod
    def from_row(cls, row: dict) -> "EKG":
        fields = {k: row[k] for k in cls.__dataclass_fields__ if k in row}
        return cls(**fields)

    # ── Signal ──

    @property
    def df(self) -> pd.DataFrame:
        return load_signal(self.file_path)

    @property
    def duration_s(self) -> float:
        return len(self.df) / EKG_SAMPLE_RATE

    def signal_window(self, start_s: float, end_s: float) -> pd.DataFrame:
        """Full-resolution slice of the signal for a time window."""
        i0 = max(0, int(start_s * EKG_SAMPLE_RATE))
        i1 = int(end_s * EKG_SAMPLE_RATE)
        return self.df.iloc[i0:i1]

    def signal_overview(self, max_points: int = 5000) -> pd.DataFrame:
        """Evenly decimated signal for a whole-recording overview plot."""
        step = max(1, len(self.df) // max_points)
        return self.df.iloc[::step]

    # ── Peaks & Herzfrequenz ──

    @property
    def peak_indices(self) -> np.ndarray:
        return _analyze(self.file_path)["peaks"]

    @property
    def peak_times_s(self) -> np.ndarray:
        return _analyze(self.file_path)["peak_times_s"]

    @property
    def peak_count(self) -> int:
        return len(self.peak_times_s)

    @property
    def _rr_s(self) -> np.ndarray:
        return _analyze(self.file_path)["rr_s"]

    @property
    def _plausible_hr(self) -> np.ndarray:
        rr = self._rr_s
        if len(rr) == 0:
            return np.array([])
        hr = 60.0 / rr
        return hr[(hr >= _HR_PLAUSIBLE[0]) & (hr <= _HR_PLAUSIBLE[1])]

    def hr_stats(self) -> dict:
        """Min/max/mean instantaneous heart rate in bpm (artifact-filtered)."""
        hr = self._plausible_hr
        if len(hr) == 0:
            return {"min": 0, "max": 0, "mean": 0}
        return {
            "min": int(hr.min()),
            "max": int(hr.max()),
            "mean": int(round(hr.mean())),
        }

    def hrv(self) -> dict:
        """SDNN and RMSSD in ms, or None values if too few beats."""
        rr_ms = self._rr_s * 1000
        # Nur plausible RR-Intervalle für die HRV verwenden.
        rr_ms = rr_ms[(rr_ms >= 60_000 / _HR_PLAUSIBLE[1])
                      & (rr_ms <= 60_000 / _HR_PLAUSIBLE[0])]
        if len(rr_ms) < 2:
            return {"sdnn": None, "rmssd": None}
        sdnn = float(np.std(rr_ms, ddof=1))
        rmssd = float(np.sqrt(np.mean(np.diff(rr_ms) ** 2)))
        return {"sdnn": round(sdnn, 1), "rmssd": round(rmssd, 1)}

    def hr_trend(self, smooth_beats: int = 7) -> pd.DataFrame:
        """Moving-average heart rate over time; columns ``time_min``, ``hr``."""
        analysis = _analyze(self.file_path)
        rr = analysis["rr_s"]
        if len(rr) < 3:
            return pd.DataFrame(columns=["time_min", "hr"])
        hr = pd.Series(60.0 / rr)
        smooth = hr.rolling(smooth_beats, center=True, min_periods=1).mean()
        return pd.DataFrame({
            "time_min": analysis["peak_times_s"][1:] / 60.0,
            "hr": smooth.to_numpy(),
        })

    # ── Holter-Kennzahlen ──

    def time_in_zone(self) -> dict:
        """Fraction of recorded time in the brady / normal / tachy band."""
        rr = self._rr_s
        rr = rr[(rr > 0) & (rr < _PAUSE_S)]
        if len(rr) == 0:
            return {"brady": 0.0, "normal": 0.0, "tachy": 0.0}
        hr = 60.0 / rr
        total = float(rr.sum())
        brady = float(rr[hr < BRADYCARDIA_BPM].sum())
        tachy = float(rr[hr > TACHYCARDIA_BPM].sum())
        normal = total - brady - tachy
        return {
            "brady": round(100 * brady / total, 1),
            "normal": round(100 * normal / total, 1),
            "tachy": round(100 * tachy / total, 1),
        }

    def pauses(self) -> dict:
        """Count of RR intervals > 2 s and the longest such pause (seconds)."""
        rr = self._rr_s
        long = rr[rr > _PAUSE_S]
        return {
            "count": int(len(long)),
            "longest_s": round(float(long.max()), 1) if len(long) else 0.0,
        }

    def ectopic_burden_pct(self) -> float:
        """Share of beats classified as irregular/ectopic, in percent."""
        labels = _analyze(self.file_path)["labels"]
        total = len(labels)
        if total == 0:
            return 0.0
        ectopic = sum(1 for lbl in labels if lbl == "irregular")
        return round(100 * ectopic / total, 1)

    def kpi_table(self) -> pd.DataFrame:
        """All key metrics as a two-column table (Kennzahl / Wert)."""
        stats = self.hr_stats()
        hrv = self.hrv()
        zones = self.time_in_zone()
        pause = self.pauses()
        minutes = self.duration_s / 60.0

        rows = [
            ("Aufnahmedauer", f"{minutes:.1f} min"),
            ("Analysierte Herzschläge", f"{self.peak_count}"),
            ("Ø Herzfrequenz", f"{stats['mean']} bpm"),
            ("Min. / Max. HR", f"{stats['min']} / {stats['max']} bpm"),
            ("SDNN (HRV)", f"{hrv['sdnn']} ms" if hrv["sdnn"] else "–"),
            ("RMSSD (HRV)", f"{hrv['rmssd']} ms" if hrv["rmssd"] else "–"),
            ("Ektopie-Last", f"{self.ectopic_burden_pct()} %"),
            ("Pausen > 2 s", f"{pause['count']} (längste {pause['longest_s']} s)"),
            ("Zeit tachykard (>100)", f"{zones['tachy']} %"),
            ("Zeit bradykard (<60)", f"{zones['brady']} %"),
        ]
        return pd.DataFrame(rows, columns=["Kennzahl", "Wert"])

    # ── Episoden & Auffälligkeiten ──

    def episodes(self) -> list[dict]:
        return _analyze(self.file_path)["episodes"]

    def episode_table(self) -> pd.DataFrame:
        """Episodes as a compact, sortable table."""
        rows = [
            {
                "Zeit": f"{ep['start_s'] / 60:.1f} min",
                "Typ": ANOMALY_LABELS.get(ep["type"], ep["type"]),
                "Dauer": f"{ep['duration_s']:.1f} s",
                "Schläge": ep["beat_count"],
                "Ø HR": f"{ep['mean_hr']:.0f} bpm",
                "start_s": ep["start_s"],
            }
            for ep in self.episodes()
        ]
        return pd.DataFrame(
            rows,
            columns=["Zeit", "Typ", "Dauer", "Schläge", "Ø HR", "start_s"],
        )

    def episode_counts(self) -> dict:
        counts = {k: 0 for k in ANOMALY_LABELS}
        for ep in self.episodes():
            counts[ep["type"]] += 1
        return counts

    def severity(self) -> str:
        """normal | attention | warning — based on episodes, not raw beats."""
        counts = self.episode_counts()
        total = sum(counts.values())
        if total == 0:
            return "normal"
        if counts["pause"] > 0 or self.ectopic_burden_pct() > 10:
            return "warning"
        return "attention"

    def episodes_in_range(self, start_s: float, end_s: float) -> list[dict]:
        return [
            ep for ep in self.episodes()
            if ep["end_s"] >= start_s and ep["start_s"] <= end_s
        ]

    # ── Auto-Befund ──

    def findings(self) -> list[str]:
        """Plain-German, automatically generated (non-diagnostic) notes."""
        stats = self.hr_stats()
        hrv = self.hrv()
        zones = self.time_in_zone()
        pause = self.pauses()
        burden = self.ectopic_burden_pct()
        notes: list[str] = []

        notes.append(
            f"Durchschnittliche Herzfrequenz {stats['mean']} bpm "
            f"(Spanne {stats['min']}–{stats['max']} bpm)."
        )

        if pause["count"] > 0:
            notes.append(
                f"{pause['count']} Pause(n) > 2 s erkannt "
                f"(längste {pause['longest_s']} s) — ärztlich abklären."
            )
        else:
            notes.append("Keine relevanten Pausen (> 2 s).")

        if burden < 1:
            notes.append(f"Geringe Ektopie-Last ({burden} % der Schläge).")
        elif burden < 10:
            notes.append(f"Moderate Ektopie-Last ({burden} % der Schläge).")
        else:
            notes.append(
                f"Hohe Ektopie-Last ({burden} % der Schläge) — auffällig."
            )

        if zones["tachy"] >= 5:
            notes.append(
                f"{zones['tachy']} % der Zeit tachykard (> 100 bpm)."
            )
        if zones["brady"] >= 5:
            notes.append(
                f"{zones['brady']} % der Zeit bradykard (< 60 bpm)."
            )

        if hrv["rmssd"] is not None:
            if hrv["rmssd"] > 100:
                notes.append(
                    f"Hohe Herzfrequenz-Variabilität (RMSSD {hrv['rmssd']} ms)."
                )
            elif hrv["rmssd"] < 20:
                notes.append(
                    f"Niedrige Herzfrequenz-Variabilität (RMSSD {hrv['rmssd']} ms)."
                )

        return notes

    # ── Plot-Daten ──

    def tachogram(self) -> pd.DataFrame:
        """RR interval over time; columns ``time_min``, ``rr_ms``."""
        analysis = _analyze(self.file_path)
        rr = analysis["rr_s"]
        if len(rr) == 0:
            return pd.DataFrame(columns=["time_min", "rr_ms"])
        return pd.DataFrame({
            "time_min": analysis["peak_times_s"][1:] / 60.0,
            "rr_ms": rr * 1000,
        })

    def poincare(self) -> pd.DataFrame:
        """Successive RR pairs for a Poincaré plot; columns ``rr_n``, ``rr_n1``."""
        rr_ms = self._rr_s * 1000
        rr_ms = rr_ms[(rr_ms >= 60_000 / _HR_PLAUSIBLE[1])
                      & (rr_ms <= 60_000 / _HR_PLAUSIBLE[0])]
        if len(rr_ms) < 2:
            return pd.DataFrame(columns=["rr_n", "rr_n1"])
        return pd.DataFrame({"rr_n": rr_ms[:-1], "rr_n1": rr_ms[1:]})

    # ── Anzeige ──

    def format_date(self) -> str:
        try:
            return pd.Timestamp(self.date).strftime("%d.%m.%Y")
        except ValueError:
            return self.date
