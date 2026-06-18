import json
import pandas as pd
from person import Person
from ekgdata import EKGdata

DB_PATH = "data/person_db.json"
SAMPLE_RATE = 360  # MIT-BIH: 360 Samples pro Sekunde


def load_person_data():
    with open(DB_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_person_list(person_data):
    return [f"{p['lastname']}, {p['firstname']}" for p in person_data]


def find_person_data_by_name(full_name, person_data):
    lastname, firstname = full_name.split(", ")
    for p in person_data:
        if p["firstname"] == firstname and p["lastname"] == lastname:
            return p
    return None


def load_person(person_dict):
    return Person(person_dict)


def load_ekg(ekg_dict):
    df = pd.read_csv(ekg_dict["result_link"], index_col=0)
    df["Zeit in ms"] = df.index / SAMPLE_RATE * 1000
    return EKGdata(ekg_dict, df)


def find_ekg_by_id(ekg_id, person_data):
    for person in person_data:
        for test in person.get("ekg_tests", []):
            if test["id"] == ekg_id:
                return load_ekg(test)
    return None
