"""EKG-Analyse-Ansicht im Holter-Stil: Auto-Befund, Kennzahlen-Tabelle,
Episoden-Tabelle mit Sprungfunktion, Signal-Plot, Live-Monitor und
HRV-Diagramme.
"""

import plotly.graph_objects as go
import streamlit as st

from cardioconnect.config import BRADYCARDIA_BPM, TACHYCARDIA_BPM
from cardioconnect.models.ekg import ANOMALY_LABELS, EKG
from cardioconnect.models.person import Person
from cardioconnect.ui.components import ekg_player

# Farben nach Rolle (dataviz-Palette): Signal = blau, Peaks = grün,
# Frequenzbänder = Status-Palette (immer mit Label gepaart).
_SIGNAL_COLOR = "#2a78d6"
_PEAK_COLOR = "#008300"
_HR_COLOR = "#e34948"
_GRID_COLOR = "#e1e0d9"
_ZONE_COLORS = {
    "brady": "#2a78d6",   # kühl = langsam
    "normal": "#0ca30c",  # grün = im Normbereich
    "tachy": "#d03b3b",   # rot = schnell
}
_ANOMALY_FILL = {
    "pause": "rgba(208, 59, 59, 0.25)",
    "irregular": "rgba(250, 178, 25, 0.22)",
    "tachycardia": "rgba(236, 131, 90, 0.20)",
    "bradycardia": "rgba(42, 120, 214, 0.15)",
}


def _severity_banner(ekg: EKG) -> None:
    severity = ekg.severity()
    counts = ekg.episode_counts()
    total = sum(counts.values())

    if severity == "normal":
        st.success(
            f"Unauffälliger Rhythmus — {ekg.peak_count} Herzschläge analysiert, "
            "keine Episoden.",
            icon="✅",
        )
        return

    headline = f"**{total} Episode(n)** erkannt · Ektopie-Last {ekg.ectopic_burden_pct()} %"
    if severity == "warning":
        st.error(headline, icon="⚠️")
    else:
        st.warning(headline, icon="⚠️")

    parts = [
        f"{ANOMALY_LABELS[t]}: **{n}**"
        for t, n in counts.items() if n > 0
    ]
    st.caption(" · ".join(parts))


def _findings(ekg: EKG) -> None:
    with st.container(border=True):
        st.markdown("**Automatischer Befund** (Hinweise, keine ärztliche Diagnose)")
        for note in ekg.findings():
            st.markdown(f"- {note}")


def _episode_table(ekg: EKG, start_key: str) -> None:
    table = ekg.episode_table()
    if table.empty:
        return

    st.markdown("##### Auffällige Episoden")
    st.caption("Zeile über das Kästchen links auswählen, um im Signal "
               "darunter zu dieser Stelle zu springen.")

    display = table.drop(columns=["start_s"])
    event = st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        height=260,
        on_select="rerun",
        selection_mode="single-row",
        key=f"episode_select_{ekg.id}",
    )
    # Die Auswahl bleibt über Reruns bestehen — nur bei einer *neuen* Auswahl
    # springen, sonst würde jede manuelle Änderung der Startzeit sofort wieder
    # überschrieben. Kein st.rerun() nötig: das Startzeit-Feld wird erst nach
    # dieser Tabelle gerendert und übernimmt den Session-State direkt.
    selected = event.selection.rows
    last_key = f"episode_last_selected_{ekg.id}"
    if selected:
        if st.session_state.get(last_key) != selected[0]:
            st.session_state[last_key] = selected[0]
            start_s = float(table["start_s"].iloc[selected[0]])
            st.session_state[start_key] = max(0.0, start_s - 2.0)
    else:
        st.session_state.pop(last_key, None)


def _detail_figure(ekg: EKG, start_s: float, end_s: float) -> go.Figure:
    fig = go.Figure()

    overview = ekg.signal_overview()
    fig.add_trace(go.Scattergl(
        x=overview["time_s"], y=overview["signal"],
        mode="lines", name="Gesamtsignal",
        line=dict(width=1, color="rgba(137, 135, 129, 0.45)"),
    ))

    window = ekg.signal_window(start_s, end_s)
    step = max(1, len(window) // 20_000)
    window = window.iloc[::step]
    fig.add_trace(go.Scattergl(
        x=window["time_s"], y=window["signal"],
        mode="lines", name="EKG-Signal",
        line=dict(width=1.4, color=_SIGNAL_COLOR),
    ))

    peak_times = ekg.peak_times_s
    in_window = (peak_times >= start_s) & (peak_times <= end_s)
    if in_window.any():
        idx = ekg.peak_indices[in_window]
        fig.add_trace(go.Scattergl(
            x=ekg.df["time_s"].iloc[idx], y=ekg.df["signal"].iloc[idx],
            mode="markers", name="R-Zacken",
            marker=dict(size=9, color=_PEAK_COLOR, symbol="triangle-down"),
        ))

    for ep in ekg.episodes_in_range(start_s, end_s):
        fig.add_vrect(
            x0=ep["start_s"], x1=ep["end_s"],
            fillcolor=_ANOMALY_FILL.get(ep["type"], "rgba(150,150,150,0.15)"),
            layer="below", line_width=0,
        )

    fig.update_layout(
        xaxis_title="Zeit [s]",
        yaxis_title="Spannung [mV]",
        height=420,
        margin=dict(l=50, r=20, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
        xaxis=dict(range=[start_s, end_s],
                   rangeslider=dict(visible=True, thickness=0.08),
                   gridcolor=_GRID_COLOR),
        yaxis=dict(gridcolor=_GRID_COLOR, fixedrange=True),
        dragmode="pan",
    )
    return fig


def _hr_trend_figure(ekg: EKG) -> go.Figure | None:
    trend = ekg.hr_trend()
    if trend.empty:
        return None

    fig = go.Figure()
    fig.add_hrect(y0=BRADYCARDIA_BPM, y1=TACHYCARDIA_BPM,
                  fillcolor="rgba(12, 163, 12, 0.06)", layer="below", line_width=0)
    fig.add_hline(y=TACHYCARDIA_BPM, line_dash="dash", line_width=1,
                  line_color="rgba(208, 59, 59, 0.6)",
                  annotation_text=f"Tachykardie (>{TACHYCARDIA_BPM})",
                  annotation_position="top right", annotation_font_size=10)
    fig.add_hline(y=BRADYCARDIA_BPM, line_dash="dash", line_width=1,
                  line_color="rgba(42, 120, 214, 0.6)",
                  annotation_text=f"Bradykardie (<{BRADYCARDIA_BPM})",
                  annotation_position="bottom right", annotation_font_size=10)
    fig.add_trace(go.Scatter(x=trend["time_min"], y=trend["hr"], mode="lines",
                             name="Herzfrequenz", line=dict(width=2, color=_HR_COLOR)))
    y_min = max(20, float(trend["hr"].min()) - 10)
    y_max = min(230, float(trend["hr"].max()) + 10)
    fig.update_layout(xaxis_title="Zeit [min]", yaxis_title="HR [bpm]",
                      yaxis_range=[y_min, y_max], height=260,
                      margin=dict(l=50, r=20, t=10, b=40), showlegend=False,
                      hovermode="x unified", xaxis=dict(gridcolor=_GRID_COLOR),
                      yaxis=dict(gridcolor=_GRID_COLOR))
    return fig


def _tachogram_figure(ekg: EKG) -> go.Figure | None:
    tacho = ekg.tachogram()
    if tacho.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=tacho["time_min"], y=tacho["rr_ms"], mode="lines",
                               line=dict(width=1, color=_SIGNAL_COLOR), name="RR"))
    fig.update_layout(xaxis_title="Zeit [min]", yaxis_title="RR-Intervall [ms]",
                      height=240, margin=dict(l=50, r=20, t=10, b=40),
                      showlegend=False, hovermode="x unified",
                      xaxis=dict(gridcolor=_GRID_COLOR),
                      yaxis=dict(gridcolor=_GRID_COLOR))
    return fig


def _poincare_figure(ekg: EKG) -> go.Figure | None:
    pc = ekg.poincare()
    if pc.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=pc["rr_n"], y=pc["rr_n1"], mode="markers",
        marker=dict(size=4, color=_SIGNAL_COLOR, opacity=0.4), name="RR-Paare",
    ))
    lo = float(min(pc["rr_n"].min(), pc["rr_n1"].min()))
    hi = float(max(pc["rr_n"].max(), pc["rr_n1"].max()))
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines",
                             line=dict(width=1, dash="dash", color="#898781"),
                             showlegend=False))
    fig.update_layout(xaxis_title="RRₙ [ms]", yaxis_title="RRₙ₊₁ [ms]",
                      height=320, margin=dict(l=50, r=20, t=10, b=40),
                      showlegend=False, xaxis=dict(gridcolor=_GRID_COLOR),
                      yaxis=dict(gridcolor=_GRID_COLOR, scaleanchor="x", scaleratio=1))
    return fig


def _zone_figure(ekg: EKG) -> go.Figure:
    zones = ekg.time_in_zone()
    labels = {"brady": "Bradykard (<60)", "normal": "Normal (60–100)",
              "tachy": "Tachykard (>100)"}
    fig = go.Figure()
    for key in ("brady", "normal", "tachy"):
        fig.add_trace(go.Bar(
            x=[zones[key]], y=["Zeit"], orientation="h",
            name=labels[key], marker_color=_ZONE_COLORS[key],
            text=f"{zones[key]:.0f} %", textposition="inside",
            insidetextanchor="middle",
        ))
    fig.update_layout(barmode="stack", height=120,
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(range=[0, 100], ticksuffix=" %",
                                 gridcolor=_GRID_COLOR),
                      yaxis=dict(showticklabels=False),
                      legend=dict(orientation="h", yanchor="bottom", y=1.05))
    return fig


def render(ekg: EKG, person: Person | None = None) -> None:
    """Full Holter-style EKG analysis for one test."""
    start_key = f"ekg_start_{ekg.id}"
    st.session_state.setdefault(start_key, 0.0)
    total_s = ekg.duration_s

    _findings(ekg)
    _severity_banner(ekg)

    st.markdown("##### Kennzahlen")
    kpis = ekg.kpi_table().set_index("Kennzahl").T
    half = (len(kpis.columns) + 1) // 2
    st.dataframe(kpis.iloc[:, :half], hide_index=True, width="stretch")
    st.dataframe(kpis.iloc[:, half:], hide_index=True, width="stretch")

    st.markdown("##### Zeit je Frequenzband")
    st.plotly_chart(_zone_figure(ekg), width="stretch",
                    key=f"ekg_zone_{ekg.id}")
    if person is not None:
        st.caption(f"Theoretische Max. HR (220 − Alter): "
                   f"{person.max_heart_rate} bpm")

    _episode_table(ekg, start_key)

    st.markdown("##### EKG-Signal")
    col_start, col_window = st.columns(2)
    with col_start:
        start_s = st.number_input(
            "Startzeit (Sekunden)", min_value=0.0,
            max_value=max(0.0, total_s - 1.0), step=5.0, format="%.1f",
            key=start_key,
        )
    with col_window:
        max_window = total_s - start_s
        window_s = st.number_input(
            "Intervalllänge (Sekunden)", min_value=1.0, max_value=max_window,
            value=min(10.0, max_window), step=5.0, format="%.1f",
            key=f"ekg_window_{ekg.id}",
        )

    st.plotly_chart(_detail_figure(ekg, start_s, start_s + window_s),
                    width="stretch", key=f"ekg_detail_{ekg.id}")

    st.markdown("##### Live-Monitor")
    ekg_player.render(ekg, initial_start_s=start_s, window_s=window_s)

    tab_hr, tab_tacho, tab_poincare = st.tabs(
        ["Herzfrequenz-Verlauf", "RR-Tachogramm", "Poincaré (HRV)"]
    )
    with tab_hr:
        fig = _hr_trend_figure(ekg)
        st.plotly_chart(fig, width="stretch", key=f"ekg_trend_{ekg.id}") \
            if fig else st.info("Zu wenige Schläge für einen Verlauf.")
    with tab_tacho:
        fig = _tachogram_figure(ekg)
        st.caption("RR-Intervall pro Schlag — gleichmäßig = regelmäßiger Rhythmus.")
        st.plotly_chart(fig, width="stretch", key=f"ekg_tacho_{ekg.id}") \
            if fig else st.info("Keine Daten.")
    with tab_poincare:
        fig = _poincare_figure(ekg)
        st.caption("Jeder Punkt = zwei aufeinanderfolgende RR-Intervalle. "
                   "Kompakte Wolke = stabile Herzfrequenz.")
        st.plotly_chart(fig, width="stretch", key=f"ekg_poincare_{ekg.id}") \
            if fig else st.info("Keine Daten.")
