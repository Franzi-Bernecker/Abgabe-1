# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CardioConnect v2 — a Streamlit web app for doctors and patients (EKG analysis, GPX activities, patient management). University software engineering project. UI language is **German**; code identifiers and docstrings are English.

## Commands

Dependency management is **PDM** (Python pinned to 3.13, venv in `.venv/`):

```
pdm install                          # install dependencies
cp secrets.toml.example .streamlit/secrets.toml   # once, before first run
pdm run streamlit run app.py         # run the app
```

Unit tests live in `tests/` (`pdm run pytest`); no linter is configured. For end-to-end checks, drive the app with `streamlit.testing.v1.AppTest` (form submit buttons appear in `at.button`; function-based pages can't be reached via `switch_page` — render them via `AppTest.from_function` with a preset `st.session_state["user"]`).

## Architecture

`app.py` (root) is a thin launcher for `cardioconnect.ui.app:run`. Layers, dependency direction top to bottom:

- **`cardioconnect/ui/`** — `app.py` (login gate + role-based `st.navigation`), `pages/` (login, dashboard, verwaltung, meine_daten), `components/` (patient_record = shared doctor/patient record view with EKG + activities tabs; ekg_analysis; ekg_player = HTML/JS canvas monitor via `st.iframe`, built from a `string.Template`; gpx_view = folium map + Plotly elevation).
- **`cardioconnect/models/`** — domain logic: `person.py` (age/BMI/max-HR), `ekg.py` (peak detection via scipy, HR/HRV, anomaly detection; module-level `load_signal`/`_analyze` are `st.cache_data`-cached and keyed by file path), `track.py` (gpxpy parsing + stats).
- **`cardioconnect/repositories/`** — SQL CRUD + upload save/validation helpers (persons, ekg_tests, activities, users).
- **`cardioconnect/`** — `db.py` (schema, FK cascades ON), `auth.py` (PBKDF2 hashing + session), `seed.py` (creates 6 demo patients/users/data when DB is empty), `config.py` (paths, constants, `get_secret`).

`data/cardioconnect.db` is generated+seeded on first run (gitignored; if still git-tracked, `git rm --cached` it). Demo passwords come from `.streamlit/secrets.toml` (`[demo_passwords]`), template in `secrets.toml.example`.

## Data formats

- `data/ekg_data/*.csv` — MIT-BIH exports, **360 Hz** (`config.EKG_SAMPLE_RATE`), 650k rows, index col + signal columns (`MLII` preferred). First load converts to a Parquet side-cache (gitignored) next to the CSV.
- `data/gpx/*.gpx` — Strava exports with `<type>` (running/cycling), 1 s trackpoints with elevation.
- `data/pictures/P<n>.jpg` maps to seeded patient n; `none.jpg` is the fallback.
- Dates are stored ISO (`YYYY-MM-DD`) in SQLite and rendered German (`DD.MM.YYYY`) in the UI.

## Conventions

- Domain dataclasses are built from DB rows via `Model.from_row(dict)`; analysis results are cached per file path, so models stay cheap to construct.
- Chart colors follow the dataviz skill: signal blue `#2a78d6`, peaks green `#008300`, anomaly overlays from the status palette (always paired with icon + label); the EKG player keeps the dark hospital-monitor look deliberately.
- `presentation.md` is a Marp slide deck (mentions the old v1 `src/` layout), not documentation.
