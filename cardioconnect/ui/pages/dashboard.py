"""Arzt-Dashboard: Patient auswählen und Akte ansehen."""

import streamlit as st

from cardioconnect.models.person import Person
from cardioconnect.repositories import persons
from cardioconnect.ui.components import patient_record


def render() -> None:
    st.title("Arzt-Dashboard")

    rows = persons.get_all()
    if not rows:
        st.warning("Keine Patienten in der Datenbank. "
                   "Neue Patienten können in der Verwaltung angelegt werden.")
        return

    options = {f"{r['lastname']}, {r['firstname']}": r for r in rows}
    choice = st.sidebar.selectbox("Patient auswählen", options.keys())

    person = Person.from_row(options[choice])
    patient_record.render(person)
