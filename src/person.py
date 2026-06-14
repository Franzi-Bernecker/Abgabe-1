import json
from datetime import date


class Person:
    # Pfad zur JSON-Datenbank
    DB_PATH = "data/person_db.json"

    def __init__(self, person_dict):
        self.id = person_dict["id"]
        self.date_of_birth = person_dict["date_of_birth"]
        self.firstname = person_dict["firstname"]
        self.lastname = person_dict["lastname"]
        self.picture_path = person_dict.get("picture_path", "data/pictures/none.jpg")
        self.ekg_tests = person_dict.get("ekg_tests", [])
        self.gender = person_dict.get("gender", "male")

    # Static Methods zum Laden/Suchen 

    @staticmethod
    def load_person_data():
        with open(Person.DB_PATH, "r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def get_person_list(person_data):
        return [f"{p['lastname']}, {p['firstname']}" for p in person_data]

    @staticmethod
    def find_person_data_by_name(full_name):
        person_data = Person.load_person_data()
        lastname, firstname = full_name.split(", ")
        for p in person_data:
            if p["firstname"] == firstname and p["lastname"] == lastname:
                return p
        return None

    @staticmethod
    def load_by_id(person_id):
        person_data = Person.load_person_data()
        for p in person_data:
            if p["id"] == person_id:
                return Person(p)
        return None

    # Berechnungen

    def calc_age(self):
        return date.today().year - self.date_of_birth

    def calc_max_heart_rate(self):
        # Standardformel: 220 - Alter
        return 220 - self.calc_age()

    def get_full_name(self):
        return f"{self.lastname}, {self.firstname}"


if __name__ == "__main__":
    persons = Person.load_person_data()
    print(Person.get_person_list(persons))
    print(Person.find_person_data_by_name("Huber, Julian"))
