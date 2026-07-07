"""Patienten-Ansicht: nur die eigene Akte, schreibgeschützt."""

import streamlit as st

from cardioconnect import auth
from cardioconnect.models.person import Person
from cardioconnect.repositories import persons
from cardioconnect.ui.components import patient_record


def render() -> None:
    st.title("Meine Daten")

    user = auth.current_user()
    person_id = user.get("person_id") if user else None
    row = persons.get_by_id(person_id) if person_id else None

    if row is None:
        st.error("Mit diesem Konto ist kein Patientenprofil verknüpft. "
                 "Bitte wenden Sie sich an Ihre Ärztin / Ihren Arzt.")
        return

    patient_record.render(Person.from_row(row), can_edit=True)
