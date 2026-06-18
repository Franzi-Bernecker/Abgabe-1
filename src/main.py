import streamlit as st
import database as db
from person import Person

st.set_page_config(page_title="CardioConnect", layout="wide")


# ── Session State initialisieren ──

if "user" not in st.session_state:
    st.session_state.user = None


# ── Login ──

def show_login():
    st.title("CardioConnect")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Benutzername")
        password = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Einloggen")

    if submitted:
        user = db.authenticate(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Benutzername oder Passwort falsch.")

    with st.expander("Demo-Accounts"):
        st.markdown(
            "| Benutzer | Passwort | Rolle |\n"
            "|----------|----------|-------|\n"
            "| arzt | arzt123 | Arzt |\n"
            "| julian | julian123 | Patient |\n"
            "| yannic | yannic123 | Patient |\n"
            "| yunus | yunus123 | Patient |"
        )


# ── Logout-Button in Sidebar ──

def show_sidebar_user_info():
    user = st.session_state.user
    role_label = "Arzt" if user["role"] == "doctor" else "Patient"
    st.sidebar.markdown(f"**{user['username']}** ({role_label})")
    if st.sidebar.button("Ausloggen"):
        st.session_state.user = None
        st.rerun()


# ── EKG anzeigen (wird von beiden Ansichten benutzt) ──

def show_ekg_for_person(person):
    if not person.ekg_tests:
        st.info("Keine EKG-Daten vorhanden.")
        return

    test_options = {f"Test {t['id']} ({t['date']})": t["id"] for t in person.ekg_tests}
    selected_test = st.selectbox("EKG-Test auswählen", options=test_options.keys())
    test_id = test_options[selected_test]

    ekg = db.find_ekg_by_id(test_id, person.id)
    if ekg is None:
        st.error("EKG-Daten konnten nicht geladen werden.")
        return

    col_hr, col_peaks = st.columns(2)
    with col_hr:
        st.metric("Durchschnittliche Herzfrequenz", f"{ekg.heart_rate} bpm")
    with col_peaks:
        st.metric("Erkannte Herzschläge", f"{len(ekg.peaks)}")

    st.plotly_chart(ekg.plot_time_series(), use_container_width=True)


# ── Arzt-Ansicht ──

def show_doctor_view():
    st.title("CardioConnect — Arzt-Dashboard")

    person_names = db.get_person_list()
    if not person_names:
        st.warning("Keine Patienten in der Datenbank.")
        return

    selected_name = st.sidebar.selectbox("Patient auswählen", options=person_names)
    person_dict = db.find_person_data_by_name(selected_name)

    if person_dict is None:
        st.error("Patient nicht gefunden.")
        return

    person = Person(person_dict)

    st.header(f"{person.firstname} {person.lastname}")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(person.picture_path, width=200)
    with col2:
        st.metric("Geburtsjahr", person.date_of_birth)
        st.metric("Alter", f"{person.calc_age()} Jahre")
        st.metric("Max. Herzfrequenz", f"{person.calc_max_heart_rate()} bpm")

    st.divider()
    show_ekg_for_person(person)


# ── Patienten-Ansicht ──

def show_patient_view():
    st.title("CardioConnect — Meine Daten")

    user = st.session_state.user
    person_dict = db.get_person_by_id(user["person_id"])

    if person_dict is None:
        st.error("Kein Patientenprofil verknüpft. Bitte den Arzt kontaktieren.")
        return

    person = Person(person_dict)

    st.header(f"{person.firstname} {person.lastname}")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(person.picture_path, width=200)
    with col2:
        st.metric("Geburtsjahr", person.date_of_birth)
        st.metric("Alter", f"{person.calc_age()} Jahre")
        st.metric("Max. Herzfrequenz", f"{person.calc_max_heart_rate()} bpm")

    st.divider()
    show_ekg_for_person(person)


# ── Routing ──

if st.session_state.user is None:
    show_login()
else:
    show_sidebar_user_info()

    if st.session_state.user["role"] == "doctor":
        show_doctor_view()
    else:
        show_patient_view()
