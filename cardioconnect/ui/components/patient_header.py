"""Kopfbereich mit Foto und Stammdaten eines Patienten (als Tabelle)."""

import base64
import mimetypes

import pandas as pd
import streamlit as st

from cardioconnect.models.person import Person

# Höhe des Stammdaten-Blocks: zwei einzeilige Dataframes plus Abstand.
_PICTURE_HEIGHT_PX = 160


def _fmt(value: float | None, unit: str = "") -> str:
    if value is None:
        return "–"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value} {unit}".strip()


def picture_html(person: Person, height_px: int) -> str:
    """Foto als HTML-Bild mit fester Höhe und festem Seitenverhältnis (4:5),
    damit der Ausschnitt auf jeder Bildschirmbreite gleich aussieht und das
    Bild in breiten Spalten nicht zu einem Querstreifen gezogen wird."""
    path = person.picture_file
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode()
    return (
        f'<img src="data:{mime};base64,{data}" alt="{person.full_name}" '
        f'style="display:block;height:{height_px}px;aspect-ratio:4/5;'
        'max-width:100%;object-fit:cover;object-position:center 25%;'
        'border-radius:0.5rem;" />'
    )


def render(person: Person) -> None:
    st.subheader(person.full_name)

    col_img, col_info = st.columns([1, 4])

    with col_img:
        st.markdown(picture_html(person, _PICTURE_HEIGHT_PX),
                    unsafe_allow_html=True)

    with col_info:
        row1 = pd.DataFrame(
            [
                {
                    "Geburtsdatum": person.format_birth_date(),
                    "Alter": f"{person.age} Jahre",
                    "Geschlecht": person.gender_label,
                    "Max. HR": f"{person.max_heart_rate} bpm",
                }
            ]
        )
        row2 = pd.DataFrame(
            [
                {
                    "Größe": _fmt(person.height_cm, "cm"),
                    "Gewicht": _fmt(person.weight_kg, "kg"),
                    "BMI": _fmt(person.bmi),
                    "Körperfett": _fmt(person.body_fat_pct, "%"),
                }
            ]
        )
        st.dataframe(row1, hide_index=True, width="stretch")
        st.dataframe(row2, hide_index=True, width="stretch")
