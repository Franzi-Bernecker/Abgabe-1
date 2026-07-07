---
marp: true
theme: gaia
class: invert
size: 16:9
paginate: true
style: |
  section {
    background: linear-gradient(160deg, #0a1628 0%, #0f2744 50%, #0a1f35 100%);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    letter-spacing: 0.01em;
  }
  section.lead {
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  section.lead h1 {
    font-size: 2.4em;
    color: #4fc3f7;
    text-shadow: 0 0 30px rgba(79, 195, 247, 0.25);
    margin-bottom: 0.1em;
  }
  section.lead p {
    color: #90caf9;
    font-size: 1.15em;
    margin-top: 0;
  }
  section.section-divider {
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
  }
  section.section-divider h1 {
    color: #4fc3f7;
    font-size: 2em;
    border: none;
  }
  section.section-divider p {
    color: #78909c;
    font-size: 1em;
  }
  section.monitor-accent h2 {
    border-bottom-color: rgba(0, 230, 118, 0.5);
  }
  section.monitor-accent li::marker {
    color: #00e676;
  }
  section.monitor-accent blockquote {
    border-left-color: #00e676;
    background: rgba(0, 230, 118, 0.08);
    color: #a5d6a7;
  }
  section.diagram {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
  }
  section.diagram h2 {
    margin-bottom: 0.4em;
  }
  section.diagram pre {
    font-size: 1em;
    line-height: 1.5;
    padding: 1.6em 2em;
    margin-top: 0.2em;
    flex: 1;
  }
  section.diagram-compact pre {
    font-size: 0.72em;
    line-height: 1.3;
    padding: 1em 1.2em;
  }
  h1 { color: #4fc3f7; font-size: 1.75em; }
  h2 {
    color: #81d4fa;
    font-size: 1.35em;
    border-bottom: 2px solid rgba(79, 195, 247, 0.35);
    padding-bottom: 0.15em;
    margin-bottom: 0.6em;
  }
  h3 { color: #90caf9; font-size: 1.05em; }
  strong { color: #4fc3f7; }
  p, li { color: #cfd8dc; line-height: 1.45; }
  ul { margin-top: 0.3em; }
  li { margin-bottom: 0.25em; }
  li::marker { color: #4fc3f7; }
  table {
    font-size: 0.78em;
    border-collapse: collapse;
    width: 100%;
    margin-top: 0.5em;
  }
  th {
    background: rgba(26, 58, 92, 0.9);
    color: #4fc3f7;
    padding: 0.45em 0.7em;
    border-bottom: 2px solid #4fc3f7;
  }
  td {
    padding: 0.4em 0.7em;
    border-bottom: 1px solid rgba(79, 195, 247, 0.12);
    color: #cfd8dc;
  }
  tr:nth-child(even) td {
    background: rgba(255, 255, 255, 0.03);
  }
  pre {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 0.68em;
    line-height: 1.3;
    background: rgba(0, 0, 0, 0.35);
    border: 1px solid rgba(79, 195, 247, 0.2);
    border-radius: 6px;
    padding: 1em 1.2em;
    color: #b0bec5;
  }
  code {
    background: rgba(30, 58, 95, 0.8);
    color: #4fc3f7;
    padding: 0.1em 0.35em;
    border-radius: 3px;
    font-size: 0.9em;
  }
  header, footer {
    color: #546e7a;
    font-size: 0.65em;
  }
  blockquote {
    border-left: 4px solid #4fc3f7;
    background: rgba(79, 195, 247, 0.08);
    padding: 0.5em 1em;
    margin: 0.5em 0;
    color: #90caf9;
    font-style: italic;
  }
---

<!-- _class: lead -->

# CardioConnect

### Kardiologie-Plattform für Ärzte & Patienten

Software Engineering · Projektplan

---

## Vision

**CardioConnect** verbindet Kardiologen und Patienten auf einer Plattform.

Ein Arzt betreut mehrere Patienten und hat Zugriff auf:

- Klinische **EKG-Daten**
- **Trainings-Aktivitäten** (Sportuhr, Strava)
- **GPS-Tracks** (Laufrouten, Radtouren)

→ Alles an einem Ort, zwei Perspektiven, eine App.

---

## Zwei Perspektiven, eine App

| Funktion | Arzt | Patient |
|----------|------|---------|
| Datensicht | Alle Patienten | Nur eigene Daten |
| Patienten anlegen | Ja | Nein |
| EKG hochladen & analysieren | Ja | Nur eigenes EKG ansehen |
| Stammdaten bearbeiten | Ja | Nein |
| Aktivitäten & GPX hochladen | Ja | Ja |

---

<!-- _class: section-divider -->

# Auth & Architektur

<p>Login, Datenmodell & Systemaufbau</p>

---

## Login & Rollen

**Echtes Login** statt manuellem Rollen-Switcher.

| Account | Passwort | Rolle | Sicht |
|---------|----------|-------|-------|
| `arzt` | `arzt123` | Arzt | Alle Patienten |
| `julian` | `julian123` | Patient | Eigenes Profil |
| `yannic` | `yannic123` | Patient | Eigenes Profil |
| `yunus` | `yunus123` | Patient | Eigenes Profil |

- Passwort-Hashing (**SHA-256 + Salt**) in SQLite
- Session via Streamlit `session_state`
- Patienten-Accounts verknüpft über `person_id`

---

<!-- _class: diagram -->

## Login-Flow

```
[Start] → Login-Screen → Credentials prüfen
              │
     ┌────────┴────────┐
     ▼                 ▼
 role=doctor      role=patient
     │                 │
     ▼                 ▼
 Arzt-Dashboard    Meine Daten
 Patient wählen    Nur eigenes Profil
```

---

<!-- _class: diagram diagram-compact -->

## Architektur

```
CardioConnect/
├── src/
│   ├── main.py          # Login, Routing, Views
│   ├── database.py      # SQLite + Auth
│   ├── person.py        # Patient-Klasse
│   ├── ekgdata.py       # EKG-Analyse + Live-Monitor
│   ├── activity.py      # Trainings (geplant)
│   └── gpxdata.py       # GPX-Tracks (geplant)
└── data/
    ├── cardioconnect.db
    ├── ekg_data/
    ├── gpx_data/
    └── pictures/
```

**Prinzipien:** Repository Pattern · OOP · Keine hardcodierten Pfade

---

<!-- _class: diagram diagram-compact -->

## Datenbankschema

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   persons    │     │    ekg_tests     │     │    users     │
├──────────────┤     ├──────────────────┤     ├──────────────┤
│ id (PK)      │──┐  │ id (PK)          │     │ id (PK)      │
│ firstname    │  ├─>│ person_id (FK)   │     │ username     │
│ lastname     │  │  │ date             │     │ password_hash│
│ date_of_birth│  │  │ result_link      │     │ role         │
│ picture_path │  │  └──────────────────┘     │ person_id(FK)│
└──────────────┘  │                             └──────────────┘
                  │     ┌──────────────────┐
                  └───> │   activities     │
                        │ person_id (FK)   │
                        │ date, type, link │
                        └──────────────────┘
```

---

<!-- _class: section-divider -->

# Features

<p>EKG-Analyse, Monitor & Extras</p>

---

## EKG-Analyse

- **Peak-Detection** — R-Zacken im EKG-Signal erkennen
- **Herzrate** — über Peak-Intervalle, Vergleich mit Max-HR (220 − Alter)
- **Zeitbereich-Auswahl** — Plotly Range Slider zum Reinzoomen
- **Caching & Downsampling** — performant bei 300k+ Datenpunkten
- **Gleitender HR-Durchschnitt** — Trends sichtbar machen
- **Live-EKG-Monitor** — Simulation wie am Krankenhausmonitor


---

## Anomalieerkennung

- **Irreguläre RR-Intervalle** — Abweichung > 2σ vom Mittel
- **Aussetzer** — Intervall doppelt so lang wie normal
- **Tachykardie / Bradykardie** — außerhalb der Normwerte
- **Visuell** — rote Markierungen im Plot + Summary-Report


---

## GPX & Aktivitäten

### GPX-Kartendarstellung
- GPX parsen mit `gpxpy` · Karte mit `folium`
- Track auf OpenStreetMap · Höhenprofil · Distanz, Pace, Höhenmeter

### Trainings-Aktivitäten
- Klasse `ActivityData` für Trainings-CSVs
- Plots: HR, Pace, Power · Zusammenfassung: Dauer, Distanz, Avg/Max HR

### Datenverwaltung
- Patienten anlegen & editieren (Arzt) · Upload mit Validierung


---

## Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Frontend / UI | **Streamlit** |
| Auth | SQLite + SHA-256, Session State |
| Datenbank | **SQLite** |
| EKG-Plots | **Plotly** |
| Karten | Folium / streamlit-folium |
| GPX-Parsing | gpxpy |
| Deployment | Streamlit Community Cloud |

---


<!-- _class: lead -->

# CardioConnect

### Fragen?

**Demo-Login:** `arzt` / `arzt123`
