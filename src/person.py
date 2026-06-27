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
        self.height_cm = person_dict.get("height_cm")
        self.weight_kg = person_dict.get("weight_kg")
        self.body_fat_pct = person_dict.get("body_fat_pct")

    def get_birth_date(self):
        """Returns the birth date as a date object, or None."""
        if isinstance(self.date_of_birth, date):
            return self.date_of_birth
        if isinstance(self.date_of_birth, str):
            try:
                return date.fromisoformat(self.date_of_birth)
            except ValueError:
                pass
        if isinstance(self.date_of_birth, int):
            return date(self.date_of_birth, 1, 1)
        return None

    def get_birth_year(self):
        bd = self.get_birth_date()
        return bd.year if bd else None

    def calc_age(self):
        bd = self.get_birth_date()
        if bd is None:
            return 0
        today = date.today()
        return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    def calc_max_heart_rate(self):
        return 220 - self.calc_age()

    def calc_bmi(self):
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            return round(self.weight_kg / (self.height_cm / 100) ** 2, 1)
        return None

    def get_full_name(self):
        return f"{self.lastname}, {self.firstname}"

    def format_birth_date(self):
        bd = self.get_birth_date()
        if bd is None:
            return "–"
        return bd.strftime("%d.%m.%Y")
