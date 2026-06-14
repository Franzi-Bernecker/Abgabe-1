# EKG-Analyse Dashboard

Eine Streamlit-Web-App zur Analyse von EKG-Daten verschiedener Probanden. Peaks (R-Zacken) werden automatisch erkannt und die Herzfrequenz berechnet.

## Architektur

```mermaid
graph LR
    A[main.py] -->|verwendet| B[Person]
    A -->|verwendet| C[EKGdata]
    B -->|liest| D[person_db.json]
    C -->|liest| E[ekg_data/*.txt]
```

## Klassendiagramm

```mermaid
classDiagram
    class Person {
        +int id
        +int date_of_birth
        +str firstname
        +str lastname
        +str picture_path
        +list ekg_tests
        +str gender
        +load_person_data()$ list
        +get_person_list(person_data)$ list
        +find_person_data_by_name(name)$ dict
        +load_by_id(person_id)$ Person
        +calc_age() int
        +calc_max_heart_rate() int
        +get_full_name() str
    }

    class EKGdata {
        +int id
        +str date
        +str result_link
        +DataFrame df
        +list peaks
        +int heart_rate
        +load_by_id(ekg_id)$ EKGdata
        +find_peaks(threshold, min_distance) list
        +estimate_hr() int
        +plot_time_series() Figure
    }

    Person "1" --> "*" EKGdata : ekg_tests
```

## Workflow

```mermaid
flowchart TD
    A[Person auswählen] --> B[Person anzeigen]
    B --> C{EKG-Daten vorhanden?}
    C -->|Ja| D[Test auswählen]
    C -->|Nein| E[Fehler anzeigen]
    D --> F[Herzfrequenz berechnen]
    D --> G[EKG-Plot mit Peaks]
```

## Installation

```bash
pdm install
```

## Starten

```bash
pdm run streamlit run src/main.py
```

Die App ist dann unter [http://localhost:8501](http://localhost:8501) erreichbar.

## Projektstruktur

```
├── src/
│   ├── main.py          # Streamlit-App (UI + Workflow)
│   ├── person.py        # Person-Klasse
│   └── ekgdata.py       # EKGdata-Klasse (Peak-Detection, HR)
├── Data/
│   ├── person_db.json   # Personen-Datenbank
│   ├── ekg_data/        # EKG-Rohdaten (1000 Hz, mV + ms)
│   └── pictures/        # Profilbilder
└── pyproject.toml
```

## Technologien

| Komponente | Technologie |
|-----------|-------------|
| UI | Streamlit |
| Datenverarbeitung | Pandas, NumPy |
| Visualisierung | Plotly |
| Paketmanager | PDM |

Autoren:
Franziska Bernecker
Laurenz Keller