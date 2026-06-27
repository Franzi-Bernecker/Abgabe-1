from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Person:

    def __init__(self, person_dict):
        self.id = person_dict["id"]
        self.date_of_birth = person_dict["date_of_birth"]
        self.firstname = person_dict["firstname"]
        self.lastname = person_dict["lastname"]
        self.picture_path = str(BASE_DIR / person_dict.get("picture_path", "data/pictures/none.jpg"))
        self.ekg_tests = person_dict.get("ekg_tests", [])
        self.gender = person_dict.get("gender", "male")

    def calc_age(self):
        try:
            birth_year = self.get_birth_year()
            return date.today().year - birth_year
        except Exception:
            return 0

    def calc_max_heart_rate(self):
        return 220 - self.calc_age()

    def get_full_name(self):
        return f"{self.lastname}, {self.firstname}"
    
    def get_birth_year(self):
        if isinstance(self.date_of_birth, int):
            return self.date_of_birth
        try:
            return date.fromisoformat(self.date_of_birth).year
        except Exception:
            return int(str(self.date_of_birth).split("-")[0])
