"""Tests für die reine EKG-Analyse-Logik (ohne Streamlit-App)."""

import numpy as np

from cardioconnect.models.ekg import _classify_beats, _find_r_peaks, _runs
from cardioconnect.config import EKG_SAMPLE_RATE


def test_runs_groups_consecutive_true_values():
    mask = np.array([False, True, True, False, True, False])
    assert _runs(mask) == [(1, 2), (4, 4)]


def test_runs_empty_and_all_true():
    assert _runs(np.array([], dtype=bool)) == []
    assert _runs(np.array([True, True])) == [(0, 1)]


def test_classify_beats_normal_rhythm():
    # 60 bpm konstant → alles normal.
    rr = np.full(50, 1.0)
    labels = _classify_beats(rr)
    assert labels == [None] * 50


def test_classify_beats_pause():
    rr = np.concatenate([np.full(30, 0.8), [2.5], np.full(30, 0.8)])
    labels = _classify_beats(rr)
    assert labels[30] == "pause"


def test_classify_beats_tachycardia_and_bradycardia():
    # 0.5 s → 120 bpm (tachykard), 1.2 s → 50 bpm (bradykard).
    tachy = _classify_beats(np.full(20, 0.5))
    brady = _classify_beats(np.full(20, 1.2))
    assert set(tachy) == {"tachycardia"}
    assert set(brady) == {"bradycardia"}


def test_classify_beats_irregular_outlier():
    # Ein einzelnes stark abweichendes RR-Intervall im sonst stabilen Rhythmus.
    rr = np.full(60, 0.8)
    rr[30] = 1.3  # +62 % Abweichung, aber keine Pause und nicht bradykard genug
    labels = _classify_beats(rr)
    assert labels[30] == "irregular"


def test_find_r_peaks_on_synthetic_signal():
    # Synthetisches EKG: 1 Hz Spitzen (60 bpm) auf flacher Grundlinie.
    duration_s = 10
    n = duration_s * EKG_SAMPLE_RATE
    signal = np.zeros(n)
    for beat in range(duration_s):
        signal[beat * EKG_SAMPLE_RATE] = 1.0
    peaks = _find_r_peaks(signal)
    # Erste Spitze bei Index 0 kann verlorengehen (Randlage), Rest muss sitzen.
    assert len(peaks) in (duration_s - 1, duration_s)
    rr = np.diff(peaks) / EKG_SAMPLE_RATE
    assert np.allclose(rr, 1.0, atol=0.01)
