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



#Erstellt die Datenbank und die Tabellen
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            date_of_birth INTEGER NOT NULL,
            gender TEXT DEFAULT 'male',
            picture_path TEXT DEFAULT 'data/pictures/none.jpg'
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
    conn.close()


#Daten lesen
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



#Daten laden

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
    """Hasht ein Passwort mit SHA-256 + Salt. Gibt (hash, salt) zurück."""
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
    """Prüft Login. Gibt User-Dict zurück oder None."""
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
    """Erstellt Default-Accounts falls noch keine User existieren."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    if count > 0:
        return

    create_user("arzt", "arzt123", role="doctor", person_id=None)
    create_user("julian", "julian123", role="patient", person_id=1)
    create_user("yannic", "yannic123", role="patient", person_id=2)
    create_user("yunus", "yunus123", role="patient", person_id=3)


# ── Initialisierung beim Import ──

init_db()
seed_default_users()
