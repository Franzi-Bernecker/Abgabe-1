"""Erst-Befüllung der Datenbank mit Demo-Patienten, Accounts und Messdaten.

Die sechs Patienten sind fiktiv, passen aber zu den Fotos in
``data/pictures/P1.jpg``–``P6.jpg``. Jeder Patient ist mit seiner
EKG-Datei (``1P_ekg.csv`` → P1, …) und seinem GPX-Track (``P1.gpx`` → P1, …)
verknüpft. Passwörter kommen aus ``st.secrets`` (Abschnitt
``[demo_passwords]``).
"""

from cardioconnect import auth
from cardioconnect.config import GPX_DIR, get_secret
from cardioconnect.db import init_db
from cardioconnect.repositories import activities, ekg_tests, persons, users

#: (firstname, lastname, date_of_birth, gender, height_cm, weight_kg, body_fat_pct)
_PATIENTS = [
    ("Ruth", "Mensah", "1958-04-12", "female", 165, 68.0, 30.1),
    ("Jonas", "Bachmann", "1996-07-03", "male", 183, 76.0, 12.8),
    ("Anita", "Sharma", "1972-09-28", "female", 168, 63.0, 26.4),
    ("Werner", "Lindemann", "1951-12-05", "male", 176, 88.0, 27.9),
    ("Lena", "Hofmann", "1999-02-17", "female", 170, 61.0, 19.5),
    ("Markus", "Vogel", "1971-06-09", "male", 181, 84.0, 21.7),
]

#: EKG-Dateien je Patient (Index 0 → P1). P4 hat zwei Aufnahmen.
_EKG_FILES = [
    [("2026-03-10", "data/ekg_data/1P_ekg.csv")],
    [("2026-04-02", "data/ekg_data/2P_ekg.csv")],
    [("2026-03-21", "data/ekg_data/3P_ekg.csv")],
    [("2026-02-14", "data/ekg_data/4P_ekg.csv"),
     ("2026-05-18", "data/ekg_data/4P_1_ekg.csv")],
    [("2026-04-27", "data/ekg_data/5P_ekg.csv")],
    [("2026-05-06", "data/ekg_data/6P_ekg.csv")],
]


def _demo_password(username: str) -> str:
    return get_secret("demo_passwords", username, default=f"{username}123")


def _seed_activity(person_id: int, gpx_filename: str) -> None:
    gpx_path = GPX_DIR / gpx_filename
    if not gpx_path.exists():
        return
    meta = activities.parse_gpx_metadata(gpx_path.read_bytes())
    if meta is None:
        return
    activities.create(
        person_id=person_id,
        date_iso=meta["date"],
        activity_type=meta["type"],
        name=meta["name"],
        file_path=f"data/gpx/{gpx_filename}",
    )


def seed_if_empty() -> None:
    """Create schema and demo data on first run; no-op afterwards."""
    init_db()
    if persons.count() > 0 or users.count_users() > 0:
        return

    pw_hash, salt = auth.hash_password(_demo_password("arzt"))
    users.create_user("arzt", pw_hash, salt, role="doctor")

    for idx, (first, last, dob, gender, height, weight, fat) in enumerate(_PATIENTS):
        pic_num = idx + 1
        person_id = persons.create(
            firstname=first,
            lastname=last,
            date_of_birth=dob,
            gender=gender,
            picture_path=f"data/pictures/P{pic_num}.jpg",
            height_cm=height,
            weight_kg=weight,
            body_fat_pct=fat,
        )

        for date_iso, ekg_path in _EKG_FILES[idx]:
            ekg_tests.create(person_id, date_iso, ekg_path)

        _seed_activity(person_id, f"P{pic_num}.gpx")

        username = first.lower()
        pw_hash, salt = auth.hash_password(_demo_password(username))
        users.create_user(username, pw_hash, salt, role="patient",
                          person_id=person_id)
