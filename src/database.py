import sqlite3
import hashlib
import secrets
from pathlib import Path

import pandas as pd
import streamlit as st

from person import Person
from ekgdata import EKGdata

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cardioconnect.db"
SAMPLE_RATE = 360


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            gender TEXT DEFAULT 'male',
            picture_path TEXT DEFAULT 'data/pictures/none.jpg',
            height_cm REAL,
            weight_kg REAL,
            body_fat_pct REAL
        );
        CREATE TABLE IF NOT EXISTS ekg_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            result_link TEXT NOT NULL,
            FOREIGN KEY (person_id) REFERENCES persons(id)
        );
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT DEFAULT 'interval',
            result_link TEXT NOT NULL,
            FOREIGN KEY (person_id) REFERENCES persons(id)
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'patient',
            person_id INTEGER,
            FOREIGN KEY (person_id) REFERENCES persons(id)
        );
    """)
    conn.commit()

    _migrate_schema(conn)

    conn.close()


def _migrate_schema(conn):
    """Add new columns to existing tables if they are missing."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(persons)").fetchall()}

    migrations = {
        "height_cm": "ALTER TABLE persons ADD COLUMN height_cm REAL",
        "weight_kg": "ALTER TABLE persons ADD COLUMN weight_kg REAL",
        "body_fat_pct": "ALTER TABLE persons ADD COLUMN body_fat_pct REAL",
    }
    for col, sql in migrations.items():
        if col not in cols:
            conn.execute(sql)

    # Migrate integer birth years to ISO date strings
    rows = conn.execute("SELECT id, date_of_birth FROM persons").fetchall()
    for row in rows:
        dob = row[1]
        if isinstance(dob, int) or (isinstance(dob, str) and dob.isdigit()):
            year = int(dob)
            conn.execute(
                "UPDATE persons SET date_of_birth = ? WHERE id = ?",
                (f"{year}-01-01", row[0]),
            )

    conn.commit()


# ── Read ──

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_all_persons():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM persons ORDER BY lastname").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_person_by_id(person_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    person_dict = dict(row)
    person_dict["ekg_tests"] = get_ekg_tests_for_person(person_id)
    return person_dict


def get_ekg_tests_for_person(person_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ekg_tests WHERE person_id = ? ORDER BY date",
        (person_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_person_list():
    persons = get_all_persons()
    return [f"{p['lastname']}, {p['firstname']}" for p in persons]


def find_person_data_by_name(full_name):
    lastname, firstname = full_name.split(", ")
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM persons WHERE firstname = ? AND lastname = ?",
        (firstname, lastname)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    person_dict = dict(row)
    person_dict["ekg_tests"] = get_ekg_tests_for_person(person_dict["id"])
    return person_dict


# ── EKG loading ──

def csv_to_parquet(csv_path):
    csv_path = BASE_DIR / csv_path
    parquet_path = csv_path.with_suffix(".parquet")

    if parquet_path.exists() and parquet_path.stat().st_mtime >= csv_path.stat().st_mtime:
        return str(parquet_path)

    df = pd.read_csv(csv_path, index_col=0)
    df.to_parquet(parquet_path, engine="pyarrow")
    return str(parquet_path)


@st.cache_data
def load_ekg_df(result_link):
    parquet_path = csv_to_parquet(result_link)
    df = pd.read_parquet(parquet_path, engine="pyarrow")
    df["Zeit in s"] = df.index / SAMPLE_RATE
    return df


def load_ekg(ekg_dict):
    df = load_ekg_df(ekg_dict["result_link"])
    ekg = EKGdata(ekg_dict, df)
    ekg.find_peaks()
    ekg.estimate_hr()
    return ekg


def find_ekg_by_id(ekg_id, person_id):
    tests = get_ekg_tests_for_person(person_id)
    for t in tests:
        if t["id"] == ekg_id:
            return load_ekg(t)
    return None


# ── Auth ──

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return pw_hash, salt


def create_user(username, password, role="patient", person_id=None):
    pw_hash, salt = hash_password(password)
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, person_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, pw_hash, salt, role, person_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


def authenticate(username, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    user = dict(row)
    pw_hash, _ = hash_password(password, user["salt"])

    if pw_hash != user["password_hash"]:
        return None

    return user


def seed_default_users():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    if count > 0:
        return

    create_user("arzt", "arzt123", role="doctor", person_id=None)
    create_user("julian", "julian123", role="patient", person_id=1)
    create_user("yannic", "yannic123", role="patient", person_id=2)
    create_user("yunus", "yunus123", role="patient", person_id=3)


def seed_default_persons():
    """Seed-Daten für die Probanden mit vollständigen Geburtsdaten und Körperdaten."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    if count > 0:
        # Update existing rows that still have placeholder dates
        updates = [
            (1, "1989-03-15", 182, 78, 14.2),
            (2, "1967-08-22", 176, 85, 22.5),
            (3, "1973-11-07", 180, 82, 18.0),
        ]
        for pid, dob, h, w, bf in updates:
            conn.execute(
                "UPDATE persons SET date_of_birth=?, height_cm=?, weight_kg=?, "
                "body_fat_pct=? WHERE id=? AND height_cm IS NULL",
                (dob, h, w, bf, pid),
            )
        conn.commit()
        conn.close()
        return
    conn.close()


# ── CRUD: Persons ──

def add_person(firstname, lastname, date_of_birth, gender="male",
               picture_path="data/pictures/none.jpg",
               height_cm=None, weight_kg=None, body_fat_pct=None):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO persons "
        "(firstname, lastname, date_of_birth, gender, picture_path, "
        "height_cm, weight_kg, body_fat_pct) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (firstname, lastname, date_of_birth, gender, picture_path,
         height_cm, weight_kg, body_fat_pct),
    )
    person_id = cur.lastrowid
    conn.commit()
    conn.close()
    return person_id


def update_person(person_id, firstname, lastname, date_of_birth, gender,
                  picture_path=None, height_cm=None, weight_kg=None,
                  body_fat_pct=None):
    conn = get_connection()
    if picture_path is not None:
        conn.execute(
            "UPDATE persons SET firstname=?, lastname=?, date_of_birth=?, "
            "gender=?, picture_path=?, height_cm=?, weight_kg=?, body_fat_pct=? "
            "WHERE id=?",
            (firstname, lastname, date_of_birth, gender, picture_path,
             height_cm, weight_kg, body_fat_pct, person_id),
        )
    else:
        conn.execute(
            "UPDATE persons SET firstname=?, lastname=?, date_of_birth=?, "
            "gender=?, height_cm=?, weight_kg=?, body_fat_pct=? WHERE id=?",
            (firstname, lastname, date_of_birth, gender,
             height_cm, weight_kg, body_fat_pct, person_id),
        )
    conn.commit()
    conn.close()


def delete_person(person_id):
    conn = get_connection()
    conn.execute("DELETE FROM ekg_tests WHERE person_id = ?", (person_id,))
    conn.execute("DELETE FROM activities WHERE person_id = ?", (person_id,))
    conn.execute("DELETE FROM users WHERE person_id = ?", (person_id,))
    conn.execute("DELETE FROM persons WHERE id = ?", (person_id,))
    conn.commit()
    conn.close()


# ── CRUD: EKG Tests ──

def add_ekg_test(person_id, date_str, result_link):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO ekg_tests (person_id, date, result_link) VALUES (?, ?, ?)",
        (person_id, date_str, result_link),
    )
    test_id = cur.lastrowid
    conn.commit()
    conn.close()
    return test_id


def delete_ekg_test(test_id):
    conn = get_connection()
    conn.execute("DELETE FROM ekg_tests WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()


# ── File helpers ──

def save_uploaded_picture(uploaded_file, person_id):
    pictures_dir = BASE_DIR / "data" / "pictures"
    pictures_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(uploaded_file.name).suffix or ".jpg"
    filename = f"P{person_id}{ext}"
    dest = pictures_dir / filename
    dest.write_bytes(uploaded_file.getbuffer())
    return f"data/pictures/{filename}"


def save_uploaded_ekg(uploaded_file, person_id):
    ekg_dir = BASE_DIR / "data" / "ekg_data"
    ekg_dir.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM ekg_tests WHERE person_id = ?", (person_id,)
    ).fetchone()[0]
    conn.close()

    idx = count + 1
    filename = f"{person_id}P_{idx}_ekg.csv"
    dest = ekg_dir / filename

    content = uploaded_file.getvalue()
    if uploaded_file.name.endswith(".txt"):
        text = content.decode("utf-8", errors="replace")
        lines = text.strip().split("\n")
        if "\t" in lines[0]:
            text = text.replace("\t", ",")
        dest.write_text(text, encoding="utf-8")
    else:
        dest.write_bytes(content)

    parquet_path = dest.with_suffix(".parquet")
    if parquet_path.exists():
        parquet_path.unlink()

    return f"data/ekg_data/{filename}"


# ── Initialisierung beim Import ──

init_db()
seed_default_users()
seed_default_persons()
