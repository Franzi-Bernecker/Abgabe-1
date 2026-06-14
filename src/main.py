import streamlit as st
from person import Person
from ekgdata import EKGdata

st.set_page_config(page_title="EKG-Analyse", layout="wide")
st.title("EKG-Analyse Dashboard")

# Personen laden und Dropdown befüllen
person_data = Person.load_person_data()
person_names = ["Bitte auswählen"] + Person.get_person_list(person_data)

selected_name = st.sidebar.selectbox("Person", options=person_names)

if selected_name == "Bitte auswählen":
    st.info("Bitte wähle eine Person in der Sidebar aus.")
else:
    person_dict = Person.find_person_data_by_name(selected_name)
    person = Person(person_dict)

    # Personen-Info anzeigen
    st.header(f"{person.firstname} {person.lastname}")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(person.picture_path, width=200)
    with col2:
        st.metric("Alter", f"{person.calc_age()} Jahre")
        st.metric("Max. Herzfrequenz", f"{person.calc_max_heart_rate()} bpm")

    st.divider()

    if not person.ekg_tests:
        st.error("Keine EKG-Daten für diese Person vorhanden.")
    else:
        # EKG-Test auswählen
        test_options = {"Bitte auswählen": None}
        test_options.update({f"Test {t['id']} ({t['date']})": t["id"] for t in person.ekg_tests})

        selected_test = st.sidebar.selectbox("EKG-Test", options=test_options.keys())
        test_id = test_options[selected_test]

        if test_id is None:
            st.info("Bitte wähle einen EKG-Test in der Sidebar aus.")
        else:
            # EKG analysieren und anzeigen
            ekg = EKGdata.load_by_id(test_id)
            ekg.find_peaks()
            hr = ekg.estimate_hr()

            col_hr, col_peaks = st.columns(2)
            with col_hr:
                st.metric("Durchschnittliche Herzfrequenz", f"{hr} bpm")
            with col_peaks:
                st.metric("Erkannte Herzschläge", f"{len(ekg.peaks)}")

            st.plotly_chart(ekg.plot_time_series(), use_container_width=True)
