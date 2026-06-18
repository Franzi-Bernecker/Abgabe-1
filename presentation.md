# Projektplan

## Vision

**CardioConnect** ist eine Plattform, die Kardiologen und Patienten verbindet. Ein Arzt betreut mehrere Patienten und hat Zugriff auf deren klinische EKG-Daten, Trainings-Aktivitäten und GPS-Tracks — alles an einem Ort.

---

## Zwei Perspektiven, eine App

| Rolle | Sicht | Funktionen |
|-------|-------|------------|
| **Arzt (Admin)** | Alle Patienten, alle Daten | Patienten anlegen/editieren, EKG-Tests hochladen, Anomalien prüfen |
| **Patient** | Nur eigene Daten | EKG-Auswertungen ansehen, Aktivitäten & GPX hochladen, Fortschritt tracken |

Der Rollenwechsel erfolgt über einen einfachen Sidebar-Switcher — kein echtes Auth nötig.

```
Sidebar:
┌─────────────────────────┐
│  Rolle waehlen:         │
│  ○ Arzt (Admin)         │
│  ○ Patient              │
│                         │
│  [Wenn Patient:]        │
│  Patient auswaehlen:    │
│  ▼ Huber, Julian        │
└─────────────────────────┘
```

---

## Architektur

```
CardioConnect/
├── src/
│   ├── main.py              # Streamlit Entry-Point, Routing
│   ├── person.py            # Person/Patient Klasse
│   ├── ekgdata.py           # EKG-Analyse Klasse
│   ├── activity.py          # Trainings-Aktivitaeten Klasse
│   ├── gpxdata.py           # GPX-Track Klasse
│   ├── database.py          # SQLite Datenbank-Layer
│   └── pages/               # Streamlit Multi-Page Struktur
│       ├── patient_view.py  # Patienten-Ansicht
│       ├── doctor_view.py   # Arzt-Ansicht (Admin)
│       └── upload.py        # Upload-Formulare
├── data/
│   ├── cardioconnect.db     # SQLite Datenbank
│   ├── ekg_data/            # EKG-Rohdaten (.txt)
│   ├── activities/          # Trainings-CSVs
│   ├── gpx_data/            # GPX-Tracks
│   └── pictures/            # Profilbilder
├── pyproject.toml
├── requirements.txt
└── README.md
```

**Prinzipien:**
- Klare Trennung von Daten-Klassen (`person.py`, `ekgdata.py`, `activity.py`) und UI (`pages/`)
- `database.py` als einziger Zugriffspunkt auf Daten (Repository Pattern)
- Keine hardcodierten Pfade — alles ueber Konstanten/Config

---

## Datenbankschema (SQLite)

Statt JSON verwenden wir SQLite fuer saubere CRUD-Operationen und natuerliche Relationen.

```
┌──────────────┐       ┌──────────────────┐
│   persons    │       │    ekg_tests     │
├──────────────┤       ├──────────────────┤
│ id (PK)      │──┐    │ id (PK)          │
│ firstname    │  │    │ person_id (FK)   │──┐
│ lastname     │  ├───>│ date             │  │
│ date_of_birth│  │    │ result_link      │  │
│ gender       │  │    └──────────────────┘  │
│ picture_path │  │                          │
└──────────────┘  │    ┌──────────────────┐  │
                  │    │   activities     │  │
                  │    ├──────────────────┤  │
                  └───>│ id (PK)          │  │
                       │ person_id (FK)   │──┘
                       │ date             │
                       │ type             │
                       │ result_link      │
                       └──────────────────┘
```

---

## Activity Diagram — Arzt-Workflow

```
[Start]
   │
   ▼
Rolle waehlen: Arzt
   │
   ▼
Patienten-Uebersicht laden
   │
   ├──────────────────────────────┐
   ▼                              ▼
Patient auswaehlen         Neuen Patient anlegen
   │                              │
   ▼                              ▼
Patienten-Daten anzeigen   Formular ausfuellen
   │                         & in DB speichern
   │                              │
   ├──────────┬──────────┐        │
   ▼          ▼          ▼        │
EKG-Tab   Aktivitaet  GPX-Tab    │
   │       -Tab          │        │
   ▼          │          ▼        │
Test         ▼       Karte mit   │
auswaehlen  Trainings- Route     │
   │        daten     anzeigen   │
   ▼        anzeigen     │       │
EKG-Plot       │         │       │
anzeigen       │         │       │
   │           │         │       │
   ├───────────┴─────────┘       │
   ▼                             │
Anomalien pruefen               │
   │                             │
   ▼                             │
[Ende] <─────────────────────────┘
```

---

## Activity Diagram — Patienten-Workflow

```
[Start]
   │
   ▼
Rolle waehlen: Patient
   │
   ▼
Eigenes Profil laden
   │
   ├──────────────────────┐
   ▼                      ▼
Daten ansehen        Daten hochladen
   │                      │
   ├────────┐             ├────────┐
   ▼        ▼             ▼        ▼
EKG-     Aktivitaets-  Aktivitaet  GPX-Track
Auswertung  Verlauf    hochladen   hochladen
   │        │          (CSV)       (GPX)
   │        │             │        │
   └────────┴─────────────┴────────┘
                  │
                  ▼
               [Ende]
```

---

## Features im Detail

### EKG-Analyse
- **Peak-Detection** zur Erkennung der R-Zacken im EKG-Signal
- **Herzrate** berechnet ueber Peak-Intervalle, Vergleich mit theoretischer Max-HR (220 - Alter)
- **Gleitender Durchschnitt** der Herzrate (Rolling Average) — macht Trends sichtbar, glaettet Rauschen
- **HRV (Herzratenvariabilitaet):** SDNN und RMSSD als Metriken fuer Stress und Fitness
- **Zeitbereich-Auswahl** per Plotly Range Slider zum Reinzoomen in das Signal
- **Caching & Downsampling** fuer performante Darstellung grosser EKG-Dateien

### Anomalieerkennung
- Irregulaere RR-Intervalle (> 2 Standardabweichungen vom Mittel)
- Aussetzer-Erkennung (Intervall doppelt so lang wie normal)
- Tachykardie/Bradykardie-Markierungen bei Abweichung von Normwerten
- Visuelle Hervorhebung im EKG-Plot (rote Bereiche) + Summary-Report

### GPX-Kartendarstellung
- Parsen von GPX-Dateien mit `gpxpy`
- Interaktive Karte mit `folium` (OpenStreetMap)
- Track als Linie auf der Karte
- Hoehenprofil als separater Plot
- Metriken: Distanz, Dauer, Avg Pace, Hoehenmeter

### Trainings-Aktivitaeten
- Eigene Klasse `ActivityData` fuer Trainings-CSVs
- Plots: Herzrate ueber Zeit, Pace ueber Zeit, Power-Kurve
- Zusammenfassung: Dauer, Distanz, Avg HR, Max HR

### Personen- & Datenverwaltung
- Patienten anlegen, editieren, loeschen (Arzt)
- EKG-Tests hochladen mit Datum und Typ (Ruhe/Belastung)
- Aktivitaeten und GPX-Tracks hochladen (Patient)
- Formular-Validierung bei allen Eingaben

---

## Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Frontend / UI | Streamlit (Multi-Page) |
| Datenbank | SQLite |
| EKG-Plots | Plotly |
| Karten | Folium / streamlit-folium |
| GPX-Parsing | gpxpy |
| Deployment | Streamlit Community Cloud |

---

## UI-Konzept

- **Farbschema:** Professionell, medizinisch — Blautoene, dezente Akzente
- **Layout:** `st.columns()` fuer Profil + Metriken nebeneinander
- **Navigation:** `st.tabs()` fuer EKG | Aktivitaeten | GPS-Tracks
- **Wide-Layout** mit eigenem Favicon und Titel "CardioConnect"
- Konsistente Plotly-Themes passend zum App-Design
