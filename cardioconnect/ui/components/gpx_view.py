"""Aktivitäten-Ansicht: Karte, Höhenprofil, Herzfrequenz, Tipps und Kennzahlen."""

import math

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from cardioconnect.models.person import Person
from cardioconnect.models.track import Activity, DEFAULT_MAX_HR

_LINE_COLOR = "#2a78d6"
_FILL_COLOR = "rgba(158, 197, 244, 0.45)"
_HR_COLOR = "#e34948"
_GRID_COLOR = "#e1e0d9"
# Hellere Routenfarbe für Kontrast auf den dunklen Kartenkacheln.
_MAP_LINE_COLOR = "#4da3ff"

_TYPE_ICONS = {"running": "🏃", "cycling": "🚴", "hiking": "🥾", "walking": "🚶"}


def _metric_row(activity: Activity) -> None:
    track = activity.track
    icon = _TYPE_ICONS.get(activity.type, "🏋️")

    row = {
        "Aktivität": f"{icon} {activity.type_label}",
        "Distanz": f"{track['distance_km']} km",
        "Dauer": activity.format_duration(),
    }
    if activity.type == "cycling":
        row["Ø Geschwindigkeit"] = f"{track['avg_speed_kmh']} km/h"
    else:
        row["Ø Pace"] = activity.format_pace()
    row["Höhenmeter"] = f"+{track['elevation_gain_m']} m"

    st.dataframe(pd.DataFrame([row]), hide_index=True, width="stretch")


def _zoom_for_bounds(lat_span: float, lon_span: float) -> int:
    """Leaflet zoom level that fits the given extent (~700x420 px viewport).

    st_folium ignores folium's ``fit_bounds``, therefore the initial zoom has
    to be computed by hand; otherwise the map opens on the whole world.
    """
    zoom_lon = math.log2(360 * (700 / 256) / max(lon_span, 1e-6))
    zoom_lat = math.log2(170 * (420 / 256) / max(lat_span, 1e-6))
    return max(2, min(17, int(min(zoom_lon, zoom_lat))))


def _track_map(activity: Activity) -> folium.Map:
    """Dark map (CartoDB Dark Matter) centred and zoomed on the route."""
    points = activity.track["points"]
    step = max(1, len(points) // 1500)
    coords = points.iloc[::step][["lat", "lon"]].values.tolist()

    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    center = [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2]
    zoom = _zoom_for_bounds(max(lats) - min(lats), max(lons) - min(lons))

    fmap = folium.Map(location=center, zoom_start=zoom,
                      tiles="CartoDB dark_matter", control_scale=True)
    folium.PolyLine(coords, color=_MAP_LINE_COLOR, weight=4,
                    opacity=0.95).add_to(fmap)
    folium.CircleMarker(coords[0], radius=6, color="#ffffff", weight=2,
                        fill=True, fill_color="#0ca30c", fill_opacity=1,
                        tooltip="Start").add_to(fmap)
    folium.CircleMarker(coords[-1], radius=6, color="#ffffff", weight=2,
                        fill=True, fill_color="#d03b3b", fill_opacity=1,
                        tooltip="Ziel").add_to(fmap)
    return fmap


def _elevation_figure(activity: Activity) -> go.Figure | None:
    points = activity.track["points"]
    if points["ele_m"].isna().all():
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=points["dist_m"] / 1000.0, y=points["ele_m"], mode="lines",
        name="Höhe", line=dict(width=2, color=_LINE_COLOR),
        fill="tozeroy", fillcolor=_FILL_COLOR,
    ))
    y_min = float(points["ele_m"].min())
    y_max = float(points["ele_m"].max())
    pad = max(5.0, (y_max - y_min) * 0.1)
    fig.update_layout(
        xaxis_title="Distanz [km]", yaxis_title="Höhe [m]",
        yaxis_range=[y_min - pad, y_max + pad], height=260,
        margin=dict(l=50, r=20, t=10, b=40), showlegend=False,
        hovermode="x unified", xaxis=dict(gridcolor=_GRID_COLOR),
        yaxis=dict(gridcolor=_GRID_COLOR),
    )
    return fig


def _hr_figure(activity: Activity) -> go.Figure | None:
    points = activity.track["points"]
    if not activity.track["has_hr"]:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=points["dist_m"] / 1000.0, y=points["hr"], mode="lines",
        name="Herzfrequenz", line=dict(width=1.6, color=_HR_COLOR),
    ))
    fig.update_layout(
        xaxis_title="Distanz [km]", yaxis_title="HR [bpm]", height=240,
        margin=dict(l=50, r=20, t=10, b=40), showlegend=False,
        hovermode="x unified", xaxis=dict(gridcolor=_GRID_COLOR),
        yaxis=dict(gridcolor=_GRID_COLOR),
    )
    return fig


def _hr_block(activity: Activity, max_hr: int) -> None:
    stats = activity.hr_stats()
    if stats is None:
        return

    st.markdown("##### Herzfrequenz")
    cols = st.columns(3)
    cols[0].metric("Ø HR", f"{stats['mean']} bpm")
    cols[1].metric("Max. HR", f"{stats['max']} bpm")
    cols[2].metric("Min. HR", f"{stats['min']} bpm")

    st.plotly_chart(_hr_figure(activity), width="stretch",
                    key=f"hr_{activity.id}")

    zones = activity.hr_zones(max_hr)
    if zones is not None:
        st.caption(f"Trainingszonen (Basis Max-HR {max_hr} bpm)")
        st.bar_chart(zones.set_index("zone"), horizontal=True,
                     color=_HR_COLOR, height=220)


def _tips_block(activity: Activity, max_hr: int) -> None:
    with st.container(border=True):
        st.markdown("**Trainings-Tipps** (automatisch, keine medizinische Beratung)")
        for tip in activity.tips(max_hr):
            st.markdown(f"- {tip}")


def render(activity: Activity, person: Person | None = None) -> None:
    """Map, elevation, heart rate, tips and stats for one GPX activity."""
    max_hr = person.max_heart_rate if person else DEFAULT_MAX_HR

    st.markdown(f"**{activity.name}** — {activity.format_date()}")
    _metric_row(activity)

    st_folium(_track_map(activity), height=420, use_container_width=True,
              returned_objects=[], key=f"map_{activity.id}")

    elevation = _elevation_figure(activity)
    if elevation is not None:
        st.markdown("##### Höhenprofil")
        st.plotly_chart(elevation, width="stretch", key=f"ele_{activity.id}")

    _hr_block(activity, max_hr)
    _tips_block(activity, max_hr)
