# CardioConnect

Kardiologie-Plattform für Ärzte und Patienten — ein Streamlit-Projekt für den
Kurs Software Engineering.

**Funktionen**

- 🔐 Login mit zwei Rollen: **Arzt** (alle Patienten, Verwaltung, Uploads) und
  **Patient** (nur eigene Daten)
- 📈 **EKG-Analyse**: R-Zacken-Erkennung (scipy), Herzfrequenz & HRV
  (SDNN/RMSSD), Anomalieerkennung (Aussetzer, irreguläre RR-Intervalle,
  Tachy-/Bradykardie), interaktiver Plotly-Plot mit Range-Slider,
  Live-EKG-Monitor mit Abspielfunktion
- 🏃 **Aktivitäten**: GPX-Tracks auf Karte (folium), Höhenprofil,
  Herzfrequenz-Zonen, Distanz, Pace, Höhenmeter
- ⚙️ **Verwaltung**: Patienten anlegen/bearbeiten/löschen, Upload von
  EKG-Dateien, GPX-Tracks und Profilbildern mit Validierung

## Setup

Voraussetzungen: Python 3.13 und [PDM](https://pdm-project.org/).

```bash
# 1. Abhängigkeiten installieren
pdm install

# 2. Secrets anlegen (Demo-Passwörter, optionaler DB-Pfad)
cp secrets.toml.example .streamlit/secrets.toml

# 3. App starten
pdm run streamlit run app.py
```

Beim ersten Start wird `data/cardioconnect.db` automatisch angelegt und mit
sechs Demo-Patienten samt EKG-Daten und GPX-Aktivitäten befüllt.

> **Deployment (Streamlit Community Cloud):** Die Cloud installiert aus
> `requirements.txt` (per `pdm export` aus dem Lockfile erzeugt). Die Secrets
> werden dort nicht als Datei abgelegt, sondern im App-Dashboard unter
> *Settings → Secrets* eingetragen — gleiches TOML-Format wie lokal.

## Login

Die Demo-Passwörter werden beim Seeding aus `.streamlit/secrets.toml`
(Abschnitt `[demo_passwords]`) gelesen und per PBKDF2-SHA256 gehasht.
Ohne Eintrag gilt der Fallback `<benutzername>123` (z. B. Arzt `arzt` /
`arzt123`) — für ein öffentliches Deployment daher unbedingt eigene
Passwörter in den Secrets setzen.

## Tests

Unit-Tests decken die reine Fachlogik ab (Personen-Kennzahlen,
Schlag-Klassifikation, R-Zacken-Erkennung auf synthetischem Signal,
Upload-Validierung, Passwort-Hashing):

```bash
pdm run pytest
```

## Architektur

```
app.py                      # Einstiegspunkt (streamlit run app.py)
cardioconnect/
├── config.py               # Pfade, Konstanten, Secrets-Zugriff
├── auth.py                 # Passwort-Hashing + Login-Session
├── db.py                   # SQLite-Verbindung + Schema
├── seed.py                 # Demo-Daten beim ersten Start
├── models/                 # Domänenlogik (Person, EKG-Analyse, GPX-Track)
├── repositories/           # Datenzugriff (Repository Pattern) + Uploads
└── ui/
    ├── app.py              # Login-Gate + rollenbasierte Navigation
    ├── pages/              # Login, Dashboard, Verwaltung, Meine Daten
    └── components/         # Patientenakte, EKG-Analyse, Player, GPX-Karte
tests/                      # Unit-Tests (pytest)
data/
├── cardioconnect.db        # SQLite (wird generiert, nicht versioniert)
├── ekg_data/               # EKG-Rohdaten (MIT-BIH, 360 Hz, CSV)
├── gpx/                    # GPX-Tracks (Strava-Export)
└── pictures/               # Profilbilder
```

Die Abhängigkeiten zeigen strikt von oben nach unten: **UI → Models →
Repositories → DB**. Eine UI-Komponente ruft nie selbst SQL auf, und ein
Model weiß nichts von Streamlit-Widgets. Dadurch bleibt die Fachlogik ohne
laufende App testbar (siehe `tests/`).

## Design-Entscheidungen

**Warum Schichten + Repository Pattern?** In frühen Versionen lagen SQL,
Analyse und UI-Code in denselben Dateien — jede Änderung an der Oberfläche
riskierte die Datenlogik. Die Aufteilung macht jede Schicht einzeln
austauschbar und testbar: Die Repositories kapseln den gesamten
SQLite-Zugriff (parametrisierte Queries, eine Datei pro Tabelle), die Models
bauen daraus per `Model.from_row(dict)` unveränderliche Dataclasses mit
abgeleiteten Kennzahlen (Alter, BMI, HRV, …).

**Warum SQLite statt „richtiger" Datenbank?** Kein Server-Setup, eine Datei,
in Python eingebaut — für eine Einzel-Instanz-App genau richtig. Das Schema
nutzt trotzdem echte Constraints: Foreign Keys mit `ON DELETE CASCADE`
(Patient löschen ⇒ EKGs, Aktivitäten und Konto verschwinden mit), `UNIQUE`
auf Benutzername und Personen-Verknüpfung. `PRAGMA foreign_keys = ON` wird
bei jeder Verbindung gesetzt, weil SQLite FKs sonst ignoriert.

**Warum Parquet-Cache für die EKG-Daten?** Eine EKG-Datei hat 650.000
Messpunkte; das CSV-Parsen dauert spürbar, und Streamlit führt das Skript
bei *jeder* Interaktion neu aus. Deshalb zwei Cache-Stufen: Beim ersten
Laden wird das CSV einmalig in eine Parquet-Datei konvertiert
(spaltenbasiert, ~10× schneller zu lesen), und `st.cache_data` hält das
Ergebnis zusätzlich im Speicher — gecacht pro Dateipfad, sodass die
Analyse (Peaks, RR-Intervalle, Episoden) genau einmal pro Datei läuft und
die Model-Objekte selbst billig konstruierbar bleiben.

**Warum Episoden statt Einzel-Schlägen?** Ein naiver Anomalie-Report würde
tausende einzelne „auffällige Schläge" listen. Echte Langzeit-EKG-Befunde
fassen stattdessen zusammen: Pausen (RR > 2 s) einzeln, ektope Schläge nur
als Runs ≥ 2 (Einzel-Ektopien gehen in die Ektopie-Last-Kennzahl), Tachy-/
Bradykardie nur, wenn sie auf der geglätteten Herzfrequenz ≥ 10 s anhält.
Die Klassifikation nutzt robuste Statistik (Median + MAD statt Mittelwert +
Standardabweichung), damit wenige Ausreißer die Schwellwerte nicht verzerren.

**Warum ein HTML/JS-Canvas-Player für den Live-Monitor?** Streamlit rendert
serverseitig — für eine flüssige 60-fps-Wiedergabe mit Abspielgeschwindigkeit
und Seekbar müsste sonst bei jedem Frame ein Rerun laufen. Der Player bekommt
das Signal einmal als JSON und animiert dann komplett im Browser
(`st.iframe` + `requestAnimationFrame`), ohne den Server zu belasten.

**Warum PBKDF2 und Secrets-Datei?** Passwörter werden nie im Klartext
gespeichert: PBKDF2-SHA256 mit 600.000 Iterationen und Salt pro Benutzer,
Vergleich über `hmac.compare_digest` (konstante Zeit, gegen Timing-Angriffe).
Die Demo-Passwörter selbst liegen in `.streamlit/secrets.toml`, die bewusst
nicht versioniert ist — im Repo liegt nur das Template `secrets.toml.example`.

**Warum Uploads inhaltlich validieren?** Die Dateiendung allein sagt nichts:
EKG-Uploads werden probeweise als CSV geparst (numerische Signalspalte,
Mindestanzahl Messwerte), GPX-Dateien müssen mindestens zwei Trackpunkte
enthalten, Bilder müssen sich von Pillow öffnen lassen. Fehlerhafte Dateien
werden mit verständlicher Meldung abgelehnt, bevor irgendetwas gespeichert
wird. Tab-getrennte `.txt`-Exporte werden beim Upload automatisch in CSV
normalisiert.

**Datenkonventionen:** Datumswerte liegen in der DB immer als ISO-String
(`YYYY-MM-DD`) und werden erst in der UI deutsch (`TT.MM.JJJJ`) formatiert —
so bleibt die Sortierung in SQL trivial. Datei-Pfade werden repo-relativ mit
`/` gespeichert, damit die DB zwischen Windows und Linux portabel ist.
