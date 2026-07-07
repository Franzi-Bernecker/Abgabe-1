"""Komplette Patienten-Akte: Kopfbereich + Tabs für EKG und Aktivitäten.

Wird vom Arzt-Dashboard und der Patienten-Ansicht gemeinsam genutzt. Über
``can_edit`` erhält der Patient die Möglichkeit, eigene GPX-Aktivitäten
hinzuzufügen oder zu entfernen.
"""

from datetime import date

import streamlit as st

from cardioconnect.models.ekg import EKG
from cardioconnect.models.person import Person
from cardioconnect.models.track import Activity
from cardioconnect.repositories import activities as activities_repo
from cardioconnect.repositories import ekg_tests as ekg_repo
from cardioconnect.ui.components import ekg_analysis, gpx_view, patient_header


def _ekg_tab(person: Person) -> None:
    tests = [EKG.from_row(t) for t in ekg_repo.get_for_person(person.id)]
    if not tests:
        st.info("Für diesen Patienten sind keine EKG-Daten vorhanden.")
        return

    if len(tests) == 1:
        selected = tests[0]
    else:
        options = {f"EKG vom {t.format_date()} (#{t.id})": t for t in tests}
        choice = st.selectbox("EKG-Test auswählen", options.keys(),
                              key=f"ekg_select_{person.id}")
        selected = options[choice]

    ekg_analysis.render(selected, person=person)


def _activities_tab(person: Person, can_edit: bool) -> None:
    entries = [Activity.from_row(a) for a in activities_repo.get_for_person(person.id)]

    if entries:
        if len(entries) == 1:
            selected = entries[0]
        else:
            options = {
                f"{a.type_label} „{a.name}“ vom {a.format_date()} (#{a.id})": a
                for a in entries
            }
            choice = st.selectbox("Aktivität auswählen", options.keys(),
                                  key=f"activity_select_{person.id}")
            selected = options[choice]
        gpx_view.render(selected, person=person)
    else:
        st.info("Für diesen Patienten sind keine Aktivitäten vorhanden.")

    if can_edit:
        st.divider()
        _activity_management(person, entries)


def _activity_management(person: Person, entries: list[Activity]) -> None:
    with st.expander("Aktivität hinzufügen / entfernen"):
        with st.form(f"patient_upload_gpx_{person.id}"):
            uploaded = st.file_uploader("GPX-Datei", type=["gpx"])
            submitted = st.form_submit_button("Hochladen", type="primary")

        if submitted:
            if uploaded is None:
                st.error("Bitte eine GPX-Datei auswählen.")
            else:
                content = uploaded.getvalue()
                meta = activities_repo.parse_gpx_metadata(content)
                if meta is None:
                    st.error("Datei ist kein gültiger GPX-Track "
                             "(mindestens zwei Trackpunkte erforderlich).")
                else:
                    path = activities_repo.save_uploaded_gpx(content, person.id)
                    activities_repo.create(
                        person.id, meta["date"] or date.today().isoformat(),
                        meta["type"], meta["name"], path,
                    )
                    st.success(f"Aktivität „{meta['name']}“ wurde hinzugefügt.")
                    st.rerun()

        if entries:
            st.caption("Vorhandene Aktivitäten")
            for activity in entries:
                c1, c2 = st.columns([5, 1])
                c1.markdown(
                    f"**{activity.name or 'Aktivität'}** — "
                    f"{activity.type_label}, {activity.format_date()}"
                )
                if c2.button("Entfernen", key=f"patient_del_act_{activity.id}"):
                    activities_repo.delete(activity.id)
                    st.rerun()


def render(person: Person, can_edit: bool = False) -> None:
    patient_header.render(person)
    st.divider()

    tab_ekg, tab_activities = st.tabs(["📈 EKG-Analyse", "🏃 Aktivitäten"])
    with tab_ekg:
        _ekg_tab(person)
    with tab_activities:
        _activities_tab(person, can_edit)
