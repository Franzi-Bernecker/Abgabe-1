"""Patientenverwaltung (nur Arzt): Anlegen, Bearbeiten, Löschen, Uploads."""

from datetime import date

import streamlit as st

from cardioconnect import auth
from cardioconnect.models.person import Person
from cardioconnect.repositories import activities as activities_repo
from cardioconnect.repositories import ekg_tests as ekg_repo
from cardioconnect.repositories import persons
from cardioconnect.ui.components.patient_header import picture_html


def render() -> None:
    st.title("Patientenverwaltung")

    if not auth.is_doctor():
        st.error("Diese Seite ist nur für Ärztinnen und Ärzte zugänglich.")
        return

    edit_id = st.session_state.get("edit_person_id")
    if edit_id == "new":
        _new_patient_form()
    elif edit_id is not None:
        _edit_patient(edit_id)
    else:
        _patient_list()


# ── Liste ──

def _patient_list() -> None:
    col_header, col_btn = st.columns([3, 1])
    with col_header:
        st.subheader("Alle Patienten")
    with col_btn:
        if st.button("＋ Neuer Patient", width="stretch", type="primary"):
            st.session_state["edit_person_id"] = "new"
            st.rerun()

    rows = persons.get_all()
    if not rows:
        st.info("Noch keine Patienten angelegt.")
        return

    for row in rows:
        person = Person.from_row(row)
        with st.container(border=True):
            c_img, c_info, c_actions = st.columns(
                [1, 5.5, 1.8], vertical_alignment="center"
            )

            with c_img:
                st.markdown(picture_html(person, 70), unsafe_allow_html=True)

            with c_info:
                st.markdown(f"**{person.full_name}**")
                parts = [
                    f"Geb. {person.format_birth_date()}",
                    f"{person.age} J.",
                    person.gender_label,
                ]
                if person.height_cm:
                    parts.append(f"{int(person.height_cm)} cm")
                if person.weight_kg:
                    parts.append(f"{person.weight_kg:g} kg")
                st.caption(" · ".join(parts))
                n_ekg = ekg_repo.count_for_person(person.id)
                n_act = activities_repo.count_for_person(person.id)
                st.caption(f"📈 {n_ekg} EKG-Tests · 🏃 {n_act} Aktivitäten")

            with c_actions:
                if st.button("Bearbeiten", key=f"edit_{person.id}",
                             width="stretch"):
                    st.session_state["edit_person_id"] = person.id
                    st.rerun()
                if st.button("Löschen", key=f"delete_{person.id}",
                             width="stretch"):
                    st.session_state[f"confirm_delete_{person.id}"] = True
                    st.rerun()

            if st.session_state.get(f"confirm_delete_{person.id}"):
                st.warning(
                    f"**{person.full_name}** wirklich löschen? "
                    "Alle EKG-Tests, Aktivitäten und das Benutzerkonto "
                    "werden ebenfalls entfernt."
                )
                d1, d2, _ = st.columns([1, 1, 4])
                if d1.button("Ja, löschen", key=f"confirm_yes_{person.id}",
                             type="primary"):
                    persons.delete(person.id)
                    st.session_state.pop(f"confirm_delete_{person.id}", None)
                    st.rerun()
                if d2.button("Abbrechen", key=f"confirm_no_{person.id}"):
                    st.session_state.pop(f"confirm_delete_{person.id}", None)
                    st.rerun()


# ── Formular-Felder (für Anlegen und Bearbeiten) ──

def _person_form_fields(person: Person | None = None) -> dict:
    """Render the master-data inputs and return their current values."""
    st.markdown("**Persönliche Daten**")
    c1, c2 = st.columns(2)
    firstname = c1.text_input("Vorname *", value=person.firstname if person else "")
    lastname = c2.text_input("Nachname *", value=person.lastname if person else "")

    c3, c4 = st.columns(2)
    default_birth = (person.birth_date if person else None) or date(1990, 1, 1)
    birth = c3.date_input(
        "Geburtsdatum *", value=default_birth,
        min_value=date(1900, 1, 1), max_value=date.today(),
    )
    gender_options = ["male", "female"]
    gender_index = gender_options.index(person.gender) \
        if person and person.gender in gender_options else 0
    gender = c4.selectbox(
        "Geschlecht", gender_options, index=gender_index,
        format_func=lambda g: "Männlich" if g == "male" else "Weiblich",
    )

    st.markdown("**Körperdaten** (optional, 0 = keine Angabe)")
    c5, c6, c7 = st.columns(3)
    height = c5.number_input("Größe (cm)", 0, 250,
                             int(person.height_cm or 0) if person else 0, 1)
    weight = c6.number_input("Gewicht (kg)", 0.0, 300.0,
                             float(person.weight_kg or 0) if person else 0.0, 0.5)
    body_fat = c7.number_input("Körperfett (%)", 0.0, 60.0,
                               float(person.body_fat_pct or 0) if person else 0.0,
                               0.5)

    return {
        "firstname": firstname.strip(),
        "lastname": lastname.strip(),
        "date_of_birth": birth.isoformat(),
        "gender": gender,
        "height_cm": height or None,
        "weight_kg": weight or None,
        "body_fat_pct": body_fat or None,
    }


def _save_picture_if_valid(uploaded, person_id: int) -> str | None:
    """Validate and store an uploaded picture; returns the path or None."""
    content = uploaded.getvalue()
    error = persons.validate_picture_bytes(content)
    if error:
        st.error(error)
        return None
    return persons.save_uploaded_picture(content, uploaded.name, person_id)


# ── Neuer Patient ──

def _new_patient_form() -> None:
    if st.button("← Zurück zur Übersicht"):
        st.session_state["edit_person_id"] = None
        st.rerun()

    st.subheader("Neuen Patienten anlegen")

    with st.form("new_patient_form"):
        values = _person_form_fields()
        picture = st.file_uploader("Profilbild (optional)",
                                   type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Patient anlegen", type="primary")

    if not submitted:
        return
    if not values["firstname"] or not values["lastname"]:
        st.error("Vor- und Nachname sind Pflichtfelder.")
        return

    person_id = persons.create(**values)

    if picture is not None:
        path = _save_picture_if_valid(picture, person_id)
        if path:
            persons.update(person_id, picture_path=path, **values)

    st.session_state["edit_person_id"] = person_id
    st.rerun()


# ── Patient bearbeiten ──

def _edit_patient(person_id: int) -> None:
    row = persons.get_by_id(person_id)
    if row is None:
        st.session_state["edit_person_id"] = None
        st.error("Patient nicht gefunden.")
        return
    person = Person.from_row(row)

    if st.button("← Zurück zur Übersicht"):
        st.session_state["edit_person_id"] = None
        st.rerun()

    st.subheader(person.full_name)

    with st.container(border=True):
        c_img, c_form = st.columns([1, 4])
        with c_img:
            st.markdown(picture_html(person, 160), unsafe_allow_html=True)

        with c_form:
            with st.form("edit_patient_form"):
                values = _person_form_fields(person)
                new_picture = st.file_uploader(
                    "Neues Profilbild", type=["jpg", "jpeg", "png"],
                )
                submitted = st.form_submit_button("Änderungen speichern",
                                                  type="primary")

            if submitted:
                if not values["firstname"] or not values["lastname"]:
                    st.error("Vor- und Nachname sind Pflichtfelder.")
                else:
                    picture_path = None
                    if new_picture is not None:
                        picture_path = _save_picture_if_valid(
                            new_picture, person_id
                        )
                    persons.update(person_id, picture_path=picture_path,
                                   **values)
                    st.success("Änderungen gespeichert.")
                    st.rerun()

    st.divider()
    _ekg_management(person_id)
    st.divider()
    _activity_management(person_id)


# ── EKG-Tests verwalten ──

def _ekg_management(person_id: int) -> None:
    st.markdown("##### EKG-Tests")

    tests = ekg_repo.get_for_person(person_id)
    if tests:
        for test in tests:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 4, 1])
                c1.markdown(f"**EKG #{test['id']}**")
                c1.caption(f"Datum: {test['date']}")
                c2.caption(f"`{test['file_path']}`")
                if c3.button("Entfernen", key=f"del_ekg_{test['id']}"):
                    ekg_repo.delete(test["id"])
                    st.rerun()
    else:
        st.info("Noch keine EKG-Tests vorhanden.")

    with st.expander("Neuen EKG-Test hochladen"):
        with st.form(f"upload_ekg_{person_id}"):
            uploaded = st.file_uploader("EKG-Datei (.csv oder .txt)",
                                        type=["csv", "txt"])
            ekg_date = st.date_input("Aufnahmedatum", value=date.today())
            submitted = st.form_submit_button("Hochladen", type="primary")

        if submitted:
            if uploaded is None:
                st.error("Bitte eine EKG-Datei auswählen.")
                return
            content = ekg_repo.normalize_ekg_text(uploaded.getvalue(),
                                                  uploaded.name)
            error = ekg_repo.validate_ekg_bytes(content)
            if error:
                st.error(error)
                return
            path = ekg_repo.save_uploaded_ekg(content, uploaded.name, person_id)
            ekg_repo.create(person_id, ekg_date.isoformat(), path)
            st.success(f"EKG-Test vom {ekg_date.strftime('%d.%m.%Y')} "
                       "wurde hinzugefügt.")
            st.rerun()


# ── Aktivitäten verwalten ──

def _activity_management(person_id: int) -> None:
    st.markdown("##### Aktivitäten (GPX)")

    entries = activities_repo.get_for_person(person_id)
    if entries:
        for activity in entries:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 4, 1])
                c1.markdown(f"**{activity['name'] or 'Aktivität'}**")
                c1.caption(f"{activity['type']} · {activity['date']}")
                c2.caption(f"`{activity['file_path']}`")
                if c3.button("Entfernen", key=f"del_act_{activity['id']}"):
                    activities_repo.delete(activity["id"])
                    st.rerun()
    else:
        st.info("Noch keine Aktivitäten vorhanden.")

    with st.expander("Neue GPX-Aktivität hochladen"):
        with st.form(f"upload_gpx_{person_id}"):
            uploaded = st.file_uploader("GPX-Datei", type=["gpx"])
            submitted = st.form_submit_button("Hochladen", type="primary")

        if submitted:
            if uploaded is None:
                st.error("Bitte eine GPX-Datei auswählen.")
                return
            content = uploaded.getvalue()
            meta = activities_repo.parse_gpx_metadata(content)
            if meta is None:
                st.error("Datei ist kein gültiger GPX-Track "
                         "(mindestens zwei Trackpunkte erforderlich).")
                return
            path = activities_repo.save_uploaded_gpx(content, person_id)
            activities_repo.create(
                person_id,
                meta["date"] or date.today().isoformat(),
                meta["type"], meta["name"], path,
            )
            st.success(f"Aktivität „{meta['name']}“ wurde hinzugefügt.")
            st.rerun()
