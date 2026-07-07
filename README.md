# 🫀 CardioConnect

**Webbasierte Kardiologie-Plattform für Ärzte und Patienten** — EKG-Analyse im
Holter-Stil, GPX-Trainingsauswertung und Patientenverwaltung in einer
Streamlit-App.

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![PDM](https://img.shields.io/badge/PDM-managed-blueviolet)
![Tests](https://img.shields.io/badge/Tests-pytest-green?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> Entstanden als Abschlussprojekt im Kurs **Software Engineering**.
> UI-Sprache ist Deutsch, Code und Docstrings sind Englisch.

---

## Inhaltsverzeichnis

- [Überblick](#überblick)
- [Features](#features)
- [Tech-Stack](#tech-stack)
- [Installation & Start](#installation--start)
- [Konfiguration](#konfiguration)
- [Benutzung](#benutzung)
- [Projektstruktur](#projektstruktur)
- [Architektur](#architektur)
- [EKG-Analyse-Pipeline](#ekg-analyse-pipeline)
- [Datenformate](#datenformate)
- [Tests](#tests)
- [Deployment](#deployment)
- [Design-Entscheidungen](#design-entscheidungen)
- [Lizenz](#lizenz)

---

## Überblick

CardioConnect bündelt zwei Perspektiven in einer Anwendung:

- **Ärztinnen und Ärzte** sehen alle Patientenakten, analysieren
  Langzeit-EKGs, werten Trainingsaktivitäten aus und verwalten Stammdaten
  sowie Datei-Uploads.
- **Patientinnen und Patienten** haben schreibgeschützten Zugriff auf die
  eigene Akte und können eigene GPX-Aktivitäten hochladen.

Beim ersten Start legt die App automatisch eine SQLite-Datenbank an und
befüllt sie mit sechs Demo-Patienten inklusive echter EKG-Aufnahmen
(MIT-BIH-Format) und GPX-Tracks — die Anwendung ist damit sofort
demonstrierbar, ohne manuelle Datenpflege.

## Features

### 🔐 Authentifizierung & Rollen
- Login mit Benutzername/Passwort, Passwörter als **PBKDF2-SHA256**-Hashes
  (600.000 Iterationen, Salt pro Benutzer, konstante Vergleichszeit)
- Zwei Rollen mit serverseitiger Prüfung: `doctor` und `patient`
- Rollenbasierte Navigation — Patienten sehen Verwaltungsseiten nicht einmal

### 📈 EKG-Analyse (Holter-Stil)
- **R-Zacken-Erkennung** über Prominenz + physiologische Refraktärzeit
  (robust gegen Baseline-Drift)
- **Herzfrequenz-Kennzahlen**: Ø/Min/Max-HR, Artefaktfilterung auf
  plausible Werte (35–210 bpm)
- **HRV-Analyse**: SDNN, RMSSD, RR-Tachogramm, Poincaré-Plot
- **Anomalie-Erkennung als Episoden**: Pausen (> 2 s), ektope Runs,
  anhaltende Tachy-/Bradykardie (≥ 10 s auf geglätteter HR) — statt
  tausender Einzel-Schlag-Meldungen
- **Automatischer Befund** in verständlichem Deutsch (explizit als
  Hinweis, nicht als Diagnose gekennzeichnet)
- **Interaktiver Signal-Plot** (Plotly, Range-Slider, Sprung zu Episoden)
  und **Live-Monitor** mit Abspielfunktion, Geschwindigkeitswahl und
  Seekbar im Stil eines Krankenhausmonitors

### 🏃 Trainings-Aktivitäten (GPX)
- Routen-Karte (folium, dunkle Kacheln, Start-/Ziel-Marker, Auto-Zoom)
- Höhenprofil, Distanz, Dauer, Pace bzw. Geschwindigkeit, Höhenmeter
- Herzfrequenz-Verlauf und **Trainingszonen** (Z1–Z5, basierend auf der
  individuellen Max-HR des Patienten)
- Regelbasierte Trainings-Tipps (Intensitätseinordnung, Erholungshinweise)

### ⚙️ Verwaltung (nur Arzt)
- Patienten anlegen, bearbeiten, löschen (mit Bestätigungsdialog;
  abhängige Daten werden per FK-Cascade mitgelöscht)
- Datei-Uploads mit **inhaltlicher Validierung** (nicht nur Dateiendung):
  EKG-CSV/TXT, GPX-Tracks, Profilbilder
- Profilbilder werden automatisch quadratisch zugeschnitten

## Tech-Stack

| Bereich | Technologie |
|---|---|
| Web-Framework | [Streamlit](https://streamlit.io/) |
| Datenhaltung | SQLite (Standardbibliothek `sqlite3`) |
| Signalverarbeitung | NumPy, SciPy (`find_peaks`), pandas |
| Visualisierung | Plotly, folium + streamlit-folium, HTML5-Canvas |
| GPX-Parsing | gpxpy |
| Bildverarbeitung | Pillow |
| Performance | PyArrow / Parquet-Cache, `st.cache_data` |
| Dependency-Management | [PDM](https://pdm-project.org/) (Python 3.13) |
| Tests | pytest |

## Installation & Start

**Voraussetzungen:** Python 3.13 und [PDM](https://pdm-project.org/).

```bash
# Repository klonen
git clone <repo-url>
cd Abgaben

# 1. Abhängigkeiten installieren (erstellt .venv/)
pdm install

# 2. Secrets anlegen (Demo-Passwörter, optionaler DB-Pfad)
cp secrets.toml.example .streamlit/secrets.toml

# 3. App starten
pdm run streamlit run app.py
```

Die App läuft anschließend unter `http://localhost:8501`. Beim ersten Start
wird `data/cardioconnect.db` angelegt und mit Demo-Daten befüllt (sechs
Patienten, sieben EKG-Aufnahmen, GPX-Aktivitäten, Benutzerkonten).

> Alternativ ohne PDM: `pip install -r requirements.txt` — die Datei wird
> per `pdm export` aus dem Lockfile erzeugt und ist damit versionsgleich.

## Konfiguration

Alle Secrets liegen in `.streamlit/secrets.toml` (nicht versioniert,
Template: [`secrets.toml.example`](secrets.toml.example)):

| Abschnitt | Schlüssel | Bedeutung |
|---|---|---|
| `[demo_passwords]` | `arzt`, `ruth`, … | Passwörter der Demo-Konten beim ersten Seeding |
| `[database]` | `path` | Optionaler alternativer DB-Pfad (relativ zum Projekt) |

Ohne Eintrag in `[demo_passwords]` gilt der Fallback
`<benutzername>123` — **für ein öffentliches Deployment unbedingt eigene
Passwörter setzen**, bevor die App erreichbar ist.

Konstanten (Abtastrate, HR-Grenzwerte, erlaubte Dateiendungen,
PBKDF2-Iterationen) sind zentral in
[`cardioconnect/config.py`](cardioconnect/config.py) definiert.

## Benutzung

| Rolle | Seite | Funktion |
|---|---|---|
| Arzt | **Dashboard** | Patient in der Sidebar wählen → vollständige Akte (EKG + Aktivitäten) |
| Arzt | **Verwaltung** | Patienten-CRUD, EKG-/GPX-/Bild-Uploads |
| Patient | **Meine Daten** | Eigene Akte einsehen, eigene GPX-Aktivitäten hochladen/entfernen |

Der Login erfolgt mit den beim Seeding angelegten Konten: ein Arzt-Konto
(`arzt`) und je ein Patienten-Konto pro Demo-Patient (Vorname,
kleingeschrieben, z. B. `ruth`). Die zugehörigen Passwörter stammen aus den
Secrets (siehe [Konfiguration](#konfiguration)).

## Projektstruktur

```
app.py                      # Einstiegspunkt (streamlit run app.py)
cardioconnect/
├── config.py               # Pfade, Konstanten, Secrets-Zugriff
├── auth.py                 # PBKDF2-Hashing + Login-Session
├── db.py                   # SQLite-Verbindung + Schema (FK-Cascades)
├── seed.py                 # Demo-Daten beim ersten Start
├── models/                 # Domänenlogik — kein Streamlit-UI, kein SQL
│   ├── person.py           #   Alter, BMI, Max-HR, Anzeige-Formatierung
│   ├── ekg.py              #   Peak-Detection, HRV, Episoden, Auto-Befund
│   └── track.py            #   GPX-Statistiken, HR-Zonen, Trainings-Tipps
├── repositories/           # Datenzugriff (Repository Pattern) + Uploads
│   ├── persons.py          #   CRUD + Profilbild-Upload
│   ├── ekg_tests.py        #   CRUD + EKG-Upload (Validierung, Normalisierung)
│   ├── activities.py       #   CRUD + GPX-Upload (Metadaten-Extraktion)
│   └── users.py            #   Benutzerkonten
└── ui/
    ├── app.py              # Login-Gate + rollenbasierte Navigation
    ├── pages/              # Login, Dashboard, Verwaltung, Meine Daten
    └── components/         # Patientenakte, EKG-Analyse, Live-Player, GPX-Karte
tests/                      # Unit-Tests (pytest)
data/
├── cardioconnect.db        # SQLite — wird generiert, nicht versioniert
├── ekg_data/               # EKG-Rohdaten (MIT-BIH, 360 Hz, CSV)
├── gpx/                    # GPX-Tracks (Strava-Export)
└── pictures/               # Profilbilder
```

## Architektur

Die Anwendung ist in vier Schichten organisiert; **Abhängigkeiten zeigen
ausschließlich nach unten**:

```
┌─────────────────────────────────────────────┐
│  UI (Streamlit)                             │  Seiten & Komponenten,
│  pages/ · components/                       │  Session-State, Widgets
├─────────────────────────────────────────────┤
│  Models (Domänenlogik)                      │  Dataclasses + Analyse:
│  Person · EKG · Activity                    │  Alter, HRV, Episoden, …
├─────────────────────────────────────────────┤
│  Repositories (Datenzugriff)                │  Parametrisiertes SQL,
│  persons · ekg_tests · activities · users   │  Upload-Validierung
├─────────────────────────────────────────────┤
│  DB / Dateisystem                           │  SQLite (FK ON) + CSV/
│  db.py · data/                              │  Parquet/GPX/Bilder
└─────────────────────────────────────────────┘
```

Konsequenzen dieser Aufteilung:

- **Kein SQL in der UI, kein Streamlit in den Repositories.** Eine
  UI-Komponente holt sich Rows über ein Repository, baut daraus per
  `Model.from_row(dict)` ein unveränderliches Domänenobjekt und rendert es.
- **Die Fachlogik ist ohne laufende App testbar** — genau das nutzen die
  Unit-Tests in `tests/`.
- **Modelle sind billig zu konstruieren**: Die teure Signal-Analyse hängt
  nicht am Objekt, sondern ist modulweit pro Dateipfad gecacht (siehe
  unten). Ein `EKG`-Objekt neu zu bauen kostet praktisch nichts.

### Datenbank-Schema

Vier Tabellen: `persons`, `ekg_tests`, `activities`, `users`. EKG-Tests,
Aktivitäten und Benutzerkonten referenzieren Personen per Foreign Key mit
`ON DELETE CASCADE` — das Löschen eines Patienten räumt alle abhängigen
Datensätze mit auf. `PRAGMA foreign_keys = ON` wird bei jeder Verbindung
gesetzt, da SQLite FK-Constraints sonst nicht durchsetzt. Messdaten
selbst (EKG-Signale, GPX-Tracks, Bilder) liegen als Dateien im
Dateisystem; die DB speichert nur repo-relative Pfade.

## EKG-Analyse-Pipeline

Eine EKG-Datei durchläuft beim ersten Öffnen folgende Schritte:

1. **Laden & Cachen** — Das CSV (650.000 Messpunkte, 360 Hz) wird einmalig
   in eine Parquet-Datei konvertiert (spaltenbasiert, deutlich schneller zu
   lesen); `st.cache_data` hält das Signal zusätzlich im Speicher.
2. **R-Zacken-Erkennung** — `scipy.signal.find_peaks` mit
   Prominenz-Schwelle (toleriert Baseline-Wandern) und Mindestabstand
   (~210 bpm Obergrenze als Refraktärzeit).
3. **Schlag-Klassifikation** — Jedes RR-Intervall wird gelabelt: Pause
   (> 2 s), ektop/irregulär (Ausreißer gegenüber Median + MAD — robuste
   Statistik, damit einzelne Extremwerte die Schwellen nicht verzerren),
   Tachykardie (> 100 bpm) oder Bradykardie (< 60 bpm).
4. **Episoden-Gruppierung** — Aufbereitung wie in einem echten
   Holter-Befund: Pausen einzeln, Ektopien nur als Runs ≥ 2 Schläge
   (Einzel-Ektopien fließen in die Ektopie-Last-Kennzahl), Tachy-/
   Bradykardie nur bei ≥ 10 s Dauer auf der geglätteten Herzfrequenz.
5. **Kennzahlen & Befund** — HR-Statistik, SDNN/RMSSD, Zeit je
   Frequenzband, Pausen-Zählung, Ektopie-Last und ein automatisch
   formulierter, nicht-diagnostischer Textbefund.

Die komplette Analyse läuft **genau einmal pro Datei** und wird gecacht —
jede weitere Interaktion (Zoom, Episodensprung, Player) arbeitet auf dem
Cache.

## Datenformate

| Daten | Format | Details |
|---|---|---|
| EKG | CSV / TXT (MIT-BIH-Export) | 360 Hz, Indexspalte + Signalspalten (`MLII` bevorzugt); TXT mit Tabs wird beim Upload zu CSV normalisiert |
| Aktivitäten | GPX 1.1 (Strava-Export) | `<type>` (running/cycling/…), 1-s-Trackpunkte mit Elevation, optional HR aus Garmin TrackPointExtension |
| Bilder | JPG / PNG | werden quadratisch zugeschnitten gespeichert |
| Datumswerte | ISO `YYYY-MM-DD` in der DB | Anzeige in der UI deutsch als `TT.MM.JJJJ`; ISO hält die SQL-Sortierung trivial |
| Datei-Pfade | repo-relativ, `/`-Separator | DB bleibt zwischen Windows und Linux portabel |

## Tests

Die Unit-Tests decken die reine Fachlogik ab — ohne laufende App und ohne
Datenbank:

- `test_person.py` — Altersberechnung (inkl. Randfälle), BMI, Max-HR,
  `from_row` mit unbekannten Spalten
- `test_ekg_analysis.py` — Schlag-Klassifikation (Pause, Tachy-/Bradykardie,
  Ektopie), Run-Gruppierung, R-Zacken-Erkennung auf synthetischem Signal
- `test_uploads.py` — EKG-CSV-Validierung, TXT-Normalisierung,
  GPX-Metadaten-Extraktion inkl. Fehlerfälle
- `test_auth.py` — PBKDF2-Roundtrip, Salt-Verhalten, falsches Passwort

```bash
pdm run pytest
```

## Deployment

### Streamlit Community Cloud

1. Repository auf GitHub pushen.
2. Auf [share.streamlit.io](https://share.streamlit.io) → *New app* →
   Repo/Branch wählen, Entrypoint `app.py`, Python 3.13.
3. Die Cloud installiert aus **`requirements.txt`** (per `pdm export` aus
   dem Lockfile erzeugt — nicht von Hand pflegen).
4. Secrets im App-Dashboard unter *Settings → Secrets* eintragen — gleiches
   TOML-Format wie die lokale `secrets.toml`. **Eigene, starke
   Demo-Passwörter setzen** (sonst greift der erratbare Fallback).

**Hinweis zur Persistenz:** Das Dateisystem der Community Cloud ist
ephemer — bei jedem Neustart (Redeploy, Inaktivität) werden Datenbank und
Uploads zurückgesetzt und die App seedet sich neu mit den Demo-Daten. Für
eine Demo-Anwendung ist dieses Selbst-Zurücksetzen erwünscht; für echten
Betrieb bräuchte es eine externe Datenbank und einen Objektspeicher.

## Design-Entscheidungen

| Entscheidung | Begründung |
|---|---|
| **Schichtenarchitektur + Repository Pattern** | UI, Fachlogik und Datenzugriff unabhängig änder- und testbar; die Vorgängerversion mischte SQL, Analyse und UI in denselben Dateien |
| **SQLite statt Server-DB** | Kein Setup, eine Datei, in Python eingebaut — für eine Einzel-Instanz-App die richtige Größe; Integrität trotzdem über echte FK-Constraints |
| **Parquet-Side-Cache + `st.cache_data`** | Streamlit führt das Skript bei jeder Interaktion neu aus; ohne Cache würde jedes Widget-Event 650k CSV-Zeilen neu parsen |
| **Anomalien als Episoden** | Orientiert an echten Langzeit-EKG-Befunden; verhindert, dass tausende Einzel-Schlag-Meldungen die Auswertung unbrauchbar machen |
| **Median + MAD statt Mittelwert + σ** | Robuste Statistik: einzelne Artefakt-Intervalle verschieben die Ektopie-Schwelle nicht |
| **HTML/JS-Canvas für den Live-Monitor** | 60-fps-Wiedergabe ist mit serverseitigen Streamlit-Reruns nicht möglich; der Player animiert vollständig im Browser |
| **PBKDF2 + `hmac.compare_digest` + Secrets-Datei** | Keine Klartext-Passwörter in Code, DB oder Git; Vergleich in konstanter Zeit gegen Timing-Angriffe |
| **Inhaltliche Upload-Validierung** | Dateiendungen sind kein Vertrauensbeweis: CSV wird probegeparst, GPX braucht ≥ 2 Trackpunkte, Bilder muss Pillow öffnen können |
| **ISO-Datum in DB, deutsches Format in UI** | Korrekte Sortierung in SQL ohne Datums-Parsing; Lokalisierung ist reine Darstellungssache |

## Lizenz

MIT — siehe [`pyproject.toml`](pyproject.toml).
