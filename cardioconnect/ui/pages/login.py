"""Login-Seite."""

import streamlit as st

from cardioconnect import auth


def render() -> None:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.title("🫀 CardioConnect")
        st.caption("Kardiologie-Plattform für Ärzte und Patienten")

        with st.form("login_form"):
            username = st.text_input("Benutzername")
            password = st.text_input("Passwort", type="password")
            submitted = st.form_submit_button(
                "Einloggen", type="primary", width="stretch"
            )

        if submitted:
            user = auth.authenticate(username, password)
            if user is None:
                st.error("Benutzername oder Passwort falsch.")
            else:
                auth.login(user)
                st.rerun()
