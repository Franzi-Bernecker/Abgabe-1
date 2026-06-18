# CardioConnect — Finale Abgabe Plan v2

## Die Vision

**CardioConnect** — eine Plattform, die Kardiologen und Patienten verbindet.

### Das Konzept

Ein Kardiologe betreut mehrere Patienten. Für jeden Patienten gibt es verschiedene Datenquellen:

1. **Klinische EKG-Daten** — vom Arzt im Krankenhaus/Praxis aufgezeichnet und hochgeladen
2. **Trainings-Aktivitäten** — vom Patienten selbst hochgeladen (Sportuhr, Strava-Export)
3. **GPS-Tracks (GPX)** — Laufrouten, Radtouren — der Patient zeigt dem Arzt "Ich bewege mich!"

### Zwei Perspektiven, eine App

| Rolle | Was sie sehen | Was sie tun können |
|-------|--------------|-------------------|
| **Arzt (Admin)** | Alle Patienten, alle Daten | Patienten anlegen/editieren, EKG-Tests hochladen, Daten analysieren, Anomalien prüfen |
| **Patient** | Nur eigene Daten | Eigene EKG-Auswertungen ansehen, Aktivitäten & GPX hochladen, Fortschritt tracken |

### Warum das funktioniert

- Alle **Pflicht-Features** der Aufgabe passen natürlich in dieses Modell rein
- Die **Extra-Features** (SQLite, GPX-Karte, HRV, Anomalieerkennung) bekommen einen echten Use-Case
- Beim **Pitch** haben wir eine klare Story: "Wir bauen eine Cardiology-Platform"
- Das Ganze ist **nicht overengineered** — wir simulieren die Rollen über einen einfachen Sidebar-Switcher (kein echtes Auth nötig für ein Uni-Projekt)

---

## Architektur

```
CardioConnect/
├── src/
│   ├── main.py              # Streamlit Entry-Point, Routing
│   ├── person.py            # Person/Patient Klasse
│   ├── ekgdata.py           # EKG-Analyse Klasse
│   ├── activity.py          # NEU: Trainings-Aktivitäten Klasse
│   ├── gpxdata.py           # NEU: GPX-Track Klasse
│   ├── database.py          # NEU: SQLite Datenbank-Layer
│   └── pages/               # NEU: Streamlit Multi-Page Struktur
│       ├── patient_view.py  # Patienten-Ansicht
│       ├── doctor_view.py   # Arzt-Ansicht (Admin)
│       └── upload.py        # Upload-Formulare (EKG, Aktivität, GPX)
├── data/                    # Lowercase! (Linux-kompatibel)
│   ├── cardioconnect.db     # NEU: SQLite Datenbank
│   ├── ekg_data/            # EKG-Rohdaten (.txt)
│   ├── activities/          # Trainings-CSVs
│   ├── gpx_data/            # NEU: GPX-Tracks
│   └── pictures/            # Profilbilder
├── pyproject.toml
├── requirements.txt         # NEU: Für Streamlit Cloud Deployment
└── README.md
```

---

## Feature-Mapping: Aufgabe → CardioConnect

### Basis-Aufgaben (36 Pkt) — Alles PFLICHT

#### 1. Geburtsjahr, Name, Bild anzeigen (2 Pkt)
**Im Kontext:** Patientenprofil-Karte mit Foto, Name, Geburtsjahr, Alter, Geschlecht
- Arzt sieht: Profil-Übersicht aller Patienten
- Patient sieht: Eigenes Profil oben auf der Seite
- **TODO:** Geburtsjahr explizit anzeigen (nicht nur Alter)

#### 2. Auswahlmöglichkeit für Tests (4 Pkt)
**Im Kontext:** Ein Patient kann mehrere EKG-Tests haben (z.B. Ruhe-EKG am 10.2., Belastungs-EKG am 11.3.)
- Dropdown mit Datum + Typ (Ruhe/Belastung) als Label
- Wenn nur 1 Test: kein Dropdown nötig, direkt anzeigen
- **TODO:** Schönere Labels, automatische Selektion bei nur 1 Test

#### 3. Testdatum und Gesamtlänge in Minuten (4 Pkt)
**Im Kontext:** Arzt will wissen: Wann war der Test? Wie lange wurde aufgezeichnet?
- Datum prominent anzeigen
- Dauer berechnen: `(max_time_ms - min_time_ms) / 60000`
- Als Metriken-Kachel: "5.1 Minuten | 10. Februar 2023"
- **TODO:** Implementieren

#### 4. EKG-Daten sinnvoll verarbeiten / Ladezeiten (2 Pkt)
**Im Kontext:** EKG-Dateien sind groß (300k+ Zeilen). Kein Arzt will 10 Sekunden warten.
- `@st.cache_data` für geladene EKG-Daten
- Downsampling für Plot-Darstellung (z.B. jeden 5. Punkt für Übersicht, volle Auflösung nur im Zoom)
- Peak-Detection Ergebnisse cachen
- **TODO:** Caching implementieren, Downsampling für Plot

#### 5. Herzrate über gesamten Zeitraum (2 Pkt)
**Im Kontext:** Der Arzt will die durchschnittliche Herzfrequenz sehen
- Aus den Peak-Intervallen berechnen (existiert schon)
- Robuster machen: Ausreißer-Peaks filtern
- Vergleich mit theoretischer Max-HR anzeigen (220 - Alter)
- **TODO:** Robustere Berechnung, Vergleich mit Max-HR

#### 6. Zeitbereich für Plots auswählen (2 Pkt)
**Im Kontext:** Ein 5-Minuten-EKG hat ~300k Datenpunkte. Der Arzt will reinzoomen können.
- Plotly Range Slider (nativ in Plotly, wenig Code)
- Zusätzlich: Streamlit Slider für Start/End-Zeit in Sekunden
- Wenn gezoomt: HR nur für den gewählten Bereich neu berechnen
- **TODO:** Range Slider in Plotly aktivieren + Streamlit Slider

#### 7. Code-Stil, OOP, Modularität (4 Pkt)
**Im Kontext:** Saubere Architektur für ein "echtes" Produkt
- Klare Trennung: Daten-Klassen (`person.py`, `ekgdata.py`, `activity.py`) vs. UI (`pages/`)
- `database.py` als einziger Zugriffspunkt auf Daten (Repository Pattern)
- Keine hardcodierten Pfade — alles über Konstanten/Config
- Snake_case überall, keine Legacy-Überreste
- `data/` statt `Data/` (Linux-Kompatibilität!)
- **TODO:** Refactoring bei der Implementierung

#### 8. Docstrings (2 Pkt)
**Im Kontext:** Professioneller Code hat Docstrings
- Google-Style Docstrings für alle Klassen, Methoden, Funktionen
- **TODO:** Beim Implementieren direkt mitschreiben

#### 9. Design optimiert & ansprechend (2 Pkt)
**Im Kontext:** CardioConnect soll wie eine echte medizinische App aussehen
- Farbschema: Professionell, medizinisch (Blautöne, Weiß, dezente Akzente)
- Layout: `st.columns()` für Profil + Metriken nebeneinander
- `st.tabs()` für EKG | Aktivitäten | GPS-Tracks
- Page Config: Wide-Layout, eigenes Favicon, Titel "CardioConnect"
- Konsistente Plotly-Themes (Farben passend zum App-Design)
- **TODO:** UI-Design als letzten Schritt polieren

#### 10. Deployment (4 Pkt)
**Im Kontext:** App muss online erreichbar sein
- Streamlit Community Cloud (kostenlos, einfach)
- `requirements.txt` aus PDM exportieren
- Pfade müssen Linux-kompatibel sein
- **TODO:** Am Ende deployen, vorher lokal testen

#### 11. Neue Personen und Tests hinzufügen (4 Pkt)
**Im Kontext:** 
- **Arzt:** Neuen Patienten anlegen (Name, Geburtsjahr, Geschlecht, Foto)
- **Arzt:** Neuen EKG-Test für einen Patienten hochladen (.txt Datei + Datum)
- **Patient:** Neue Aktivität/GPX hochladen
- Formular mit Validierung
- **TODO:** Upload-Seite bauen

#### 12. Bestehende Personen editieren (4 Pkt)
**Im Kontext:**
- **Arzt:** Patientendaten ändern (Name korrigieren, Foto aktualisieren, etc.)
- Edit-Button am Profil → Formular mit vorausgefüllten Feldern
- Änderungen in DB speichern
- **TODO:** Edit-Modus implementieren

---

### Freie Aufgaben — Unsere Auswahl

#### A. SQLite Datenbank (6 Pkt) ✅ MACHEN
**Warum im CardioConnect-Kontext:**
- JSON skaliert nicht — stell dir 500 Patienten in einer JSON-Datei vor
- SQLite macht CRUD-Operationen (Create/Read/Update/Delete) sauber
- Relationen sind natürlich: Patient → hat viele EKG-Tests, hat viele Aktivitäten
- Migration: Bestehendes JSON → SQLite Converter-Script

**Datenbankschema:**
```sql
CREATE TABLE persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    date_of_birth INTEGER NOT NULL,
    gender TEXT DEFAULT 'male',
    picture_path TEXT DEFAULT 'data/pictures/none.jpg'
);

CREATE TABLE ekg_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    result_link TEXT NOT NULL,
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    type TEXT DEFAULT 'interval',  -- 'interval', 'gpx', 'run', etc.
    result_link TEXT NOT NULL,
    FOREIGN KEY (person_id) REFERENCES persons(id)
);
```

**Aufwand:** ~2h

#### B. Gleitender Durchschnitt der Herzrate (2 Pkt) ✅ MACHEN
**Warum im CardioConnect-Kontext:**
- Ein einzelner HR-Wert sagt wenig — der Verlauf zeigt dem Arzt das Bild
- Rolling Average glättet Rauschen, macht Trends sichtbar
- Besonders relevant beim Belastungs-EKG: HR steigt an → Plateau → Erholung

**Umsetzung:**
- RR-Intervalle (Peak-zu-Peak) → in BPM umrechnen → `rolling(window=10).mean()`
- Als zweiten Plot oder Overlay im EKG-Chart
- Fensterbreite per Slider einstellbar

**Aufwand:** ~30 min

#### C. Herzratenvariabilität / HRV (2 Pkt) ✅ MACHEN
**Warum im CardioConnect-Kontext:**
- HRV ist DER Indikator für Stress, Fitness, autonomes Nervensystem
- Jeder Sportler mit einer Garmin/Apple Watch kennt HRV
- Arzt kann HRV-Werte über mehrere Besuche vergleichen

**Umsetzung:**
- **SDNN:** Standardabweichung aller RR-Intervalle (1 Zahl, einfach)
- **RMSSD:** Root Mean Square of Successive Differences (empfindlicher für kurze Variabilität)
- Anzeige als Metriken-Kacheln: "SDNN: 45ms | RMSSD: 32ms"
- Optional: Poincaré-Plot (RR(n) vs RR(n+1)) — sieht beeindruckend aus

**Aufwand:** ~45 min

#### D. Anomalieerkennung in EKG-Daten (6 Pkt) ✅ MACHEN
**Warum im CardioConnect-Kontext:**
- DAS Killer-Feature für einen Kardiologen — "Zeig mir wo etwas nicht stimmt"
- Automatische Warnung bei unregelmäßigen Herzschlägen

**Umsetzung (pragmatisch, keine KI nötig):**
1. **Irreguläre RR-Intervalle:** Wenn ein Peak-Abstand > 2 Standardabweichungen vom Mittel abweicht → markieren
2. **Aussetzer:** Intervall plötzlich doppelt so lang wie normal → "Aussetzer" / mögliches Vorhofflimmern
3. **Tachykardie/Bradykardie:** HR-Bereiche die außerhalb von Normwerten liegen markieren
4. **Visuell:** Rote Bereiche im EKG-Plot, Summary mit Anzahl der Anomalien

**Aufwand:** ~2-3h

#### E. GPX-Kartendarstellung (4 Pkt) ✅ MACHEN
**Warum im CardioConnect-Kontext:**
- Patient lädt seinen Lauf als GPX hoch → Arzt sieht die Route auf einer Karte
- Zeigt: "Patient bewegt sich regelmäßig, läuft 5km-Runden"
- Visuell stark, beeindruckt beim Pitch

**Umsetzung:**
- `gpxpy` zum Parsen der GPX-Datei
- `folium` oder `streamlit-folium` für interaktive Karte
- Track als Linie auf OpenStreetMap
- Höhenprofil als zweiten Plot darunter
- Metriken: Distanz, Dauer, Avg Pace, Höhenmeter

**GPX-Testdaten besorgen:**
- Option 1: Eigenen Lauf aus Strava/Garmin exportieren (am authentischsten)
- Option 2: Von Wikiloc.com eine kurze Route runterladen
- Option 3: Mit Python ein realistisches GPX generieren (Punkte entlang einer echten Straße)
- 2-3 GPX-Dateien reichen für die Demo

**Aufwand:** ~2h

#### F. Aktivitäts-Daten nutzen (EIGENES EXTRA) ✅ MACHEN
**Warum:**
- Die `activity.csv` liegt schon im Repo und wird NICHT genutzt — das wäre verschenkt
- Neue Klasse `ActivityData` mit eigenem Tab in der UI
- Plots: HR über Zeit, Pace über Zeit, Power-Kurve
- Trainings-Zusammenfassung: Dauer, Distanz, Avg HR, Max HR

**Aufwand:** ~1.5h

---

### NICHT machen (und warum)

| Feature | Warum nicht |
|---------|------------|
| .fit-Dateien einlesen | Braucht `fitparse` Lib, proprietäres Garmin-Format, GPX ist einfacher und zeigt dasselbe |
| Echtes Auth-System | Overengineered für Uni-Projekt, Rollen-Switcher reicht |
| Krankenkassen-Integration | Moralisch fragwürdig und weit außerhalb des Scopes |

---

## Rollen-System (simpel aber effektiv)

Kein echtes Login nötig. Stattdessen:

```
Sidebar:
┌─────────────────────┐
│ 🔄 Rolle wählen:    │
│ ○ Arzt (Admin)      │
│ ○ Patient            │
│                     │
│ [Wenn Patient:]     │
│ Patient auswählen:  │
│ ▼ Huber, Julian     │
└─────────────────────┘
```

**Arzt sieht:**
- Alle Patienten in einer Übersicht
- Patient auswählen → alle Daten (EKG, Aktivitäten, GPX)
- Patienten hinzufügen / editieren
- EKG-Tests hochladen
- Anomalie-Report

**Patient sieht:**
- Nur eigenes Profil + eigene Daten
- Eigene EKG-Auswertungen
- Eigene Aktivitäten hochladen (CSV, GPX)
- Kein Zugriff auf andere Patienten, kein Editieren von Stammdaten

---

## Implementierungs-Reihenfolge

### Phase 1: Foundation (vor dem Pitch morgen, ~2h)
> Ziel: Genug fertig haben um das Konzept live zu zeigen

1. **Pfade fixen** (`Data/` → `data/`) — 10 min
2. **`database.py`** erstellen — SQLite Schema + Migration von JSON — 1h
3. **`person.py`** refactoren auf SQLite — 30 min
4. **Basis-UI aufräumen** — Geburtsjahr anzeigen, Testdatum + Dauer — 20 min

### Phase 2: Kern-Features (~4h)
5. **`ekgdata.py` verbessern** — Caching, Downsampling, robustere Peaks — 1h
6. **Zeitbereich-Auswahl** — Plotly Range Slider — 20 min
7. **Gleitender HR-Durchschnitt** — Rolling Average Plot — 30 min
8. **HRV-Berechnung** — SDNN, RMSSD als Metriken — 45 min
9. **Personen hinzufügen + editieren** — Formulare + DB-Writes — 1.5h

### Phase 3: Extras (~4h)
10. **Anomalieerkennung** — Irreguläre Intervalle markieren — 2h
11. **`activity.py`** — Activity-CSV Klasse + Plots — 1h
12. **`gpxdata.py`** — GPX Parser + Folium-Karte — 1.5h
13. **GPX-Testdaten** besorgen und einbinden — 30 min

### Phase 4: Polish & Deploy (~2h)
14. **Rollen-System** — Sidebar Switcher (Arzt/Patient) — 45 min
15. **UI-Design** — Farben, Layout, Tabs, Wide-Mode — 45 min
16. **Docstrings** überall — 30 min
17. **Deployment** — requirements.txt + Streamlit Cloud — 30 min
18. **README** aktualisieren — 15 min

---

## Punkterechnung

| Kategorie | Feature | Punkte |
|-----------|---------|--------|
| **Basis** | Geburtsjahr/Name/Bild | 2 |
| **Basis** | Test-Auswahl | 4 |
| **Basis** | Testdatum + Dauer | 4 |
| **Basis** | EKG-Performance (Caching) | 2 |
| **Basis** | Herzrate gesamt | 2 |
| **Basis** | Zeitbereich-Auswahl | 2 |
| **Basis** | Code-Stil / OOP | 4 |
| **Basis** | Docstrings | 2 |
| **Basis** | Design | 2 |
| **Basis** | Deployment | 4 |
| **Basis** | Personen/Tests hinzufügen | 4 |
| **Basis** | Personen editieren | 4 |
| **Basis gesamt** | | **36** |
| **Extra** | SQLite Datenbank | 6 |
| **Extra** | Gleitender HR-Durchschnitt | 2 |
| **Extra** | HRV | 2 |
| **Extra** | Anomalieerkennung | 6 |
| **Extra** | GPX-Karte | 4 |
| **Extra** | Activity-Daten (eigenes) | 2-4 |
| **Extra gesamt** | | **22-24** |
| | | |
| **TOTAL** | | **58-60 / 60** |

---


### Live zeigen
- App starten, als Arzt einloggen
- Patient auswählen, EKG ansehen
- Reinzoomen, Anomalien zeigen
- Auf Patient-Ansicht wechseln
- GPX-Route auf Karte zeigen

### Zeitplan argumentieren
- "Grundgerüst steht, Datenmodell definiert, Architektur klar"
- "~12h Implementierung, 2 Personen, 1 Woche Zeit"
