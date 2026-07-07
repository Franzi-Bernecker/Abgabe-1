"""App-Shell: Konfiguration, Login-Gate und rollenbasierte Navigation."""

import streamlit as st

from cardioconnect import __version__, auth
from cardioconnect.seed import seed_if_empty
from cardioconnect.ui.pages import dashboard, login, meine_daten, verwaltung


# Pinnt den Footer an das untere Ende der Sidebar; das Padding reserviert
# Platz, damit er den restlichen Sidebar-Inhalt nicht überdeckt.
_SIDEBAR_FOOTER_CSS = """
<style>
[data-testid="stSidebarUserContent"] {
    padding-bottom: 12rem;
}
section[data-testid="stSidebar"] .st-key-sidebar_footer {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    padding: 0 1.5rem 0.75rem;
}
</style>
"""


def _sidebar_footer(user: dict) -> None:
    """User info, logout and version pinned to the bottom of the sidebar."""
    role_label = "Arzt" if user["role"] == "doctor" else "Patient"
    label = user["username"]
    if label.casefold() != role_label.casefold():
        label += f" · {role_label}"

    st.sidebar.markdown(_SIDEBAR_FOOTER_CSS, unsafe_allow_html=True)
    with st.sidebar.container(key="sidebar_footer"):
        st.divider()
        st.caption(f"Angemeldet als **{label}**")
        if st.button("Ausloggen", width="stretch", icon="🚪"):
            auth.logout()
            st.rerun()
        st.caption(f"CardioConnect v{__version__}")


def run() -> None:
    """Entry point, called from the root ``app.py``."""
    st.set_page_config(
        page_title="CardioConnect",
        page_icon="🫀",
        layout="wide",
    )

    seed_if_empty()

    user = auth.current_user()
    if user is None:
        # Versteckte Navigation, damit nach dem Ausloggen keine veraltete
        # Sidebar-Navigation stehen bleibt.
        st.navigation(
            [st.Page(login.render, title="Anmelden", url_path="login")],
            position="hidden",
        ).run()
        return

    if user["role"] == "doctor":
        pages = [
            st.Page(dashboard.render, title="Dashboard",
                    icon="📊", url_path="dashboard", default=True),
            st.Page(verwaltung.render, title="Verwaltung",
                    icon="⚙️", url_path="verwaltung"),
        ]
    else:
        pages = [
            st.Page(meine_daten.render, title="Meine Daten",
                    icon="🫀", url_path="meine-daten", default=True),
        ]

    # Seiteninhalt zuerst rendern, damit Sidebar-Widgets der Seite (z. B. die
    # Patientenauswahl) direkt unter der Navigation stehen und der Footer folgt.
    navigation = st.navigation(pages)
    navigation.run()
    _sidebar_footer(user)
