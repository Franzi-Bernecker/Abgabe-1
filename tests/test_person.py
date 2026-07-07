"""Tests für das Person-Domänenmodell (Alter, BMI, from_row)."""

from datetime import date

from cardioconnect.models.person import Person


def _person(**overrides) -> Person:
    defaults = dict(
        id=1,
        firstname="Ruth",
        lastname="Mensah",
        date_of_birth="1958-04-12",
        gender="female",
        picture_path="data/pictures/P1.jpg",
    )
    defaults.update(overrides)
    return Person(**defaults)


def test_from_row_ignores_unknown_keys():
    row = {
        "id": 3,
        "firstname": "Anita",
        "lastname": "Sharma",
        "date_of_birth": "1972-09-28",
        "gender": "female",
        "picture_path": "data/pictures/P3.jpg",
        "unbekannte_spalte": "wird ignoriert",
    }
    person = Person.from_row(row)
    assert person.id == 3
    assert person.full_name == "Anita Sharma"


def test_age_counts_full_years():
    today = date.today()
    # 20. Geburtstag war gestern → 20 Jahre.
    born = today.replace(year=today.year - 20)
    person = _person(date_of_birth=born.isoformat())
    assert person.age == 20


def test_age_before_birthday_this_year():
    today = date.today()
    born = date(today.year - 30, today.month, today.day)
    # Geburtstag einen Tag in der Zukunft → noch 29.
    if today.month == 12 and today.day == 31:
        expected = 30  # Randfall Silvester: Geburtstag heute.
    else:
        born = born.replace(
            month=today.month if today.day < 28 else today.month % 12 + 1,
            day=today.day + 1 if today.day < 28 else 1,
        )
        expected = 29
    person = _person(date_of_birth=born.isoformat())
    assert person.age == expected


def test_age_invalid_date_is_zero():
    person = _person(date_of_birth="kein-datum")
    assert person.birth_date is None
    assert person.age == 0


def test_max_heart_rate():
    today = date.today()
    born = today.replace(year=today.year - 40)
    person = _person(date_of_birth=born.isoformat())
    assert person.max_heart_rate == 220 - 40


def test_bmi():
    person = _person(height_cm=180.0, weight_kg=81.0)
    assert person.bmi == 25.0


def test_bmi_missing_data_is_none():
    assert _person().bmi is None
    assert _person(height_cm=180.0).bmi is None
