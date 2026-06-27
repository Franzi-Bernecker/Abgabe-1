import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import database as db
from person import Person
from datetime import date


st.set_page_config(page_title="CardioConnect", layout="wide")


# ── Session State ──

if "user" not in st.session_state:
    st.session_state.user = None
if "doctor_page" not in st.session_state:
    st.session_state.doctor_page = "dashboard"
if "edit_person_id" not in st.session_state:
    st.session_state.edit_person_id = None


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


# ── Sidebar ──

def _nav_button(label, icon, target_page):
    """Styled sidebar nav button. Returns True if this page is active."""
    is_active = st.session_state.doctor_page == target_page
    btn_type = "primary" if is_active else "secondary"
    if st.sidebar.button(
        f"{icon}  {label}",
        key=f"nav_{target_page}",
        type=btn_type,
        width="stretch",
    ):
        st.session_state.doctor_page = target_page
        st.session_state.edit_person_id = None
        st.rerun()
    return is_active


def show_sidebar_user_info():
    user = st.session_state.user
    role_label = "Arzt" if user["role"] == "doctor" else "Patient"
    st.sidebar.markdown(f"### {user['username']}")
    st.sidebar.caption(role_label)
    st.sidebar.divider()


def show_sidebar_nav():
    _nav_button("Dashboard", "📊", "dashboard")
    _nav_button("Verwaltung", "⚙️", "verwaltung")
    st.sidebar.divider()
    if st.sidebar.button("Ausloggen", width="stretch"):
        st.session_state.user = None
        st.session_state.doctor_page = "dashboard"
        st.session_state.edit_person_id = None
        st.rerun()


def show_sidebar_patient():
    if st.sidebar.button("Ausloggen", width="stretch"):
        st.session_state.user = None
        st.rerun()


# ── Patient info card (shared between dashboard and patient view) ──

def _format_opt(value, unit=""):
    if value is None:
        return "–"
    if isinstance(value, float) and value == int(value):
        value = int(value)
    return f"{value} {unit}".strip()


def show_patient_header(person):
    col_img, col_info = st.columns([1, 4])
    with col_img:
        st.image(person.picture_path, width=180)
    with col_info:
        st.subheader(f"{person.firstname} {person.lastname}")

        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        with r1c1:
            st.metric("Geburtsdatum", person.format_birth_date())
        with r1c2:
            st.metric("Alter", f"{person.calc_age()} Jahre")
        with r1c3:
            st.metric("Geschlecht",
                       "Männlich" if person.gender == "male" else "Weiblich")
        with r1c4:
            st.metric("Max. HR", f"{person.calc_max_heart_rate()} bpm")

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            st.metric("Größe", _format_opt(person.height_cm, "cm"))
        with r2c2:
            st.metric("Gewicht", _format_opt(person.weight_kg, "kg"))
        with r2c3:
            bmi = person.calc_bmi()
            st.metric("BMI", _format_opt(bmi))
        with r2c4:
            st.metric("Körperfett", _format_opt(person.body_fat_pct, "%"))


# ── EKG Analyse Tab ──

def _format_duration(seconds):
    m, s = divmod(int(seconds), 60)
    if m > 0:
        return f"{m} min {s} s"
    return f"{s} s"


def _anomaly_type_label(atype):
    return {
        "irregular": "Irreguläres Intervall",
        "dropout": "Aussetzer / Pause",
        "tachycardia": "Tachykardie",
        "bradycardia": "Bradykardie",
    }.get(atype, atype)


def _anomaly_type_icon(atype):
    return {
        "irregular": "⚡",
        "dropout": "⏸️",
        "tachycardia": "🔺",
        "bradycardia": "🔻",
    }.get(atype, "⚠️")


def show_ekg_analyse(ekg, person=None):
    total_s = ekg.duration_s
    total_peaks = ekg.total_peaks_count
    hr_stats = ekg.get_hr_stats()
    hrv = ekg.calc_hrv()
    anomaly_summary = ekg.get_anomaly_summary()
    anomalies = ekg.detect_anomalies()

    max_hr_patient = None
    if person is not None and hasattr(person, "calc_max_heart_rate"):
        try:
            max_hr_patient = person.calc_max_heart_rate()
        except Exception:
            pass

    max_hr_str = f"{hr_stats['max']} bpm"
    if max_hr_patient and hr_stats["max"] > 0:
        diff = hr_stats["max"] - max_hr_patient
        max_hr_str += f" ({diff:+d} vs. theor. Max)"

    hrv_sdnn = f"{hrv['sdnn']} ms" if hrv["sdnn"] is not None else "–"
    hrv_rmssd = f"{hrv['rmssd']} ms" if hrv["rmssd"] is not None else "–"

    st.markdown(f"""
<table style="width:100%; border-collapse:collapse; font-size:0.85em; margin-bottom:4px;">
  <tr style="border-bottom:2px solid rgba(128,128,128,0.2);">
    <th style="text-align:left;padding:4px 8px;color:#888;font-weight:600;" colspan="2">Aufnahme</th>
    <th style="text-align:left;padding:4px 8px;color:#888;font-weight:600;" colspan="2">Herzfrequenz</th>
    <th style="text-align:left;padding:4px 8px;color:#888;font-weight:600;" colspan="2">HRV</th>
  </tr>
  <tr>
    <td style="padding:3px 8px;color:#aaa;">Datum</td>
    <td style="padding:3px 8px;font-weight:500;">{ekg.date or '–'}</td>
    <td style="padding:3px 8px;color:#aaa;">Ø HR</td>
    <td style="padding:3px 8px;font-weight:500;">{hr_stats['mean']} bpm</td>
    <td style="padding:3px 8px;color:#aaa;">SDNN</td>
    <td style="padding:3px 8px;font-weight:500;">{hrv_sdnn}</td>
  </tr>
  <tr>
    <td style="padding:3px 8px;color:#aaa;">Dauer</td>
    <td style="padding:3px 8px;font-weight:500;">{_format_duration(total_s)}</td>
    <td style="padding:3px 8px;color:#aaa;">Min HR</td>
    <td style="padding:3px 8px;font-weight:500;">{hr_stats['min']} bpm</td>
    <td style="padding:3px 8px;color:#aaa;">RMSSD</td>
    <td style="padding:3px 8px;font-weight:500;">{hrv_rmssd}</td>
  </tr>
  <tr>
    <td style="padding:3px 8px;color:#aaa;">Herzschläge</td>
    <td style="padding:3px 8px;font-weight:500;">{total_peaks}</td>
    <td style="padding:3px 8px;color:#aaa;">Max HR</td>
    <td style="padding:3px 8px;font-weight:500;">{max_hr_str}</td>
    <td style="padding:3px 8px;color:#aaa;"></td>
    <td style="padding:3px 8px;"></td>
  </tr>
</table>
""", unsafe_allow_html=True)

    jump_key = f"_jump_anomaly_{ekg.id}"

    if anomaly_summary["severity"] == "normal":
        st.success(f"Keine Auffälligkeiten — {total_peaks} Herzschläge analysiert.")
    else:
        counts = anomaly_summary["counts"]
        if anomaly_summary["severity"] == "warning":
            st.error(f"**{anomaly_summary['total']} Auffälligkeiten** erkannt")
        else:
            st.warning(f"**{anomaly_summary['total']} Auffälligkeiten** erkannt")

        parts = []
        labels_short = {"dropout": "Aussetzer", "irregular": "Irregulär",
                        "tachycardia": "Tachykardie", "bradycardia": "Bradykardie"}
        for atype in ["dropout", "irregular", "tachycardia", "bradycardia"]:
            if counts[atype] > 0:
                parts.append(f"{labels_short[atype]}: **{counts[atype]}**")
        if parts:
            st.caption(" · ".join(parts))

        with st.expander("Anomalie-Details — klicke auf eine Zeile um dorthin zu springen"):
            if anomalies:
                for idx, a in enumerate(anomalies):
                    t = a["time_s"]
                    rr_str = f" · RR {a['rr_ms']} ms" if a.get("rr_ms") else ""
                    label = (f"{_anomaly_type_icon(a['type'])} "
                             f"**{_anomaly_type_label(a['type'])}** — "
                             f"{t:.1f} s · HR {a['hr']:.0f} bpm{rr_str}")
                    if st.button(label, key=f"anomaly_jump_{ekg.id}_{idx}",
                                 width="stretch"):
                        st.session_state[jump_key] = max(0.0, t - 2.0)
                        st.rerun()

    st.divider()

    st.markdown("##### EKG-Signal")

    default_start = st.session_state.pop(jump_key, 0.0)

    col_start, col_len = st.columns(2)
    with col_start:
        start_s = st.number_input(
            "Startzeit (Sekunden)",
            min_value=0.0,
            max_value=max(0.0, total_s - 1),
            value=min(default_start, total_s - 1),
            step=1.0,
            format="%.1f",
            key=f"start_{ekg.id}",
        )
    with col_len:
        max_window = total_s - start_s
        window_s = st.number_input(
            "Intervalllänge (Sekunden)",
            min_value=1.0,
            max_value=max_window,
            value=min(10.0, max_window),
            step=1.0,
            format="%.1f",
            key=f"window_{ekg.id}",
        )

    _show_ekg_player(ekg, start_s, window_s)

    hr_fig = ekg.plot_hr_trend()
    if hr_fig:
        st.markdown("##### Herzfrequenz-Verlauf")
        st.plotly_chart(hr_fig, width="stretch", key=f"hr_trend_{ekg.id}")


# ── Combined EKG Player ──

def _show_ekg_player(ekg, initial_start_s, window_s):
    signal = ekg.df[ekg.signal_col].values.tolist()
    sample_rate = ekg.SAMPLE_RATE

    if ekg.peaks is None:
        ekg.find_peaks()
    peak_times_s = ekg.df["Zeit in s"].iloc[ekg.peaks].values.tolist()

    anomalies_raw = ekg.detect_anomalies()
    anomaly_regions = []
    for a in anomalies_raw:
        color_map = {
            "dropout": "rgba(231,76,60,0.3)",
            "irregular": "rgba(243,156,18,0.25)",
            "tachycardia": "rgba(255,87,34,0.2)",
            "bradycardia": "rgba(52,152,219,0.2)",
        }
        anomaly_regions.append({
            "s": a["time_s"],
            "e": a["time_end_s"],
            "c": color_map.get(a["type"], "rgba(231,76,60,0.2)"),
            "t": a["type"][:4],
        })

    data_json = json.dumps(signal)
    peaks_json = json.dumps(peak_times_s)
    anomalies_json = json.dumps(anomaly_regions)
    initial_sample = int(initial_start_s * sample_rate)
    window_samples = int(window_s * sample_rate)
    total_time = f"{int(ekg.duration_s // 60)}:{int(ekg.duration_s % 60):02d}"

    html = f"""
    <div id="ekg-player" style="background:#111827;border-radius:8px;padding:16px;font-family:-apple-system,system-ui,sans-serif;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span id="hr-display" style="font-size:1.6em;color:#00ff41;font-family:monospace;font-weight:700;">-- bpm</span>
        <span id="time-display" style="font-size:0.85em;color:#6b7280;font-family:monospace;">0:00 / {total_time}</span>
      </div>
      <canvas id="ekg-canvas" style="width:100%;height:300px;display:block;border-radius:4px;"></canvas>
      <div style="margin-top:10px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <div id="seekbar-container" style="flex:1;height:20px;cursor:pointer;position:relative;display:flex;align-items:center;">
            <div style="width:100%;height:4px;background:#1f2937;border-radius:2px;position:relative;">
              <div id="seekbar-fill" style="height:100%;width:0%;background:#3b82f6;border-radius:2px;"></div>
              <div id="seekbar-thumb" style="position:absolute;top:50%;left:0%;transform:translate(-50%,-50%);width:12px;height:12px;background:#3b82f6;border-radius:50%;"></div>
            </div>
          </div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:10px;">
        <button id="btn-play" onclick="togglePlay()" style="padding:6px 16px;border:none;border-radius:4px;background:#3b82f6;color:#fff;font-weight:600;cursor:pointer;font-size:0.85em;">▶ Abspielen</button>
        <button onclick="resetPlayer()" style="padding:6px 16px;border:none;border-radius:4px;background:#374151;color:#9ca3af;cursor:pointer;font-size:0.85em;">⏮ Reset</button>
        <div style="display:flex;gap:4px;margin-left:8px;">
          <button class="spd-btn" data-speed="0.5" onclick="setSpeed(0.5)" style="padding:4px 10px;border:1px solid #374151;border-radius:3px;background:transparent;color:#9ca3af;cursor:pointer;font-size:0.8em;">0.5x</button>
          <button class="spd-btn active" data-speed="1" onclick="setSpeed(1)" style="padding:4px 10px;border:1px solid #3b82f6;border-radius:3px;background:rgba(59,130,246,0.15);color:#3b82f6;cursor:pointer;font-size:0.8em;">1x</button>
          <button class="spd-btn" data-speed="2" onclick="setSpeed(2)" style="padding:4px 10px;border:1px solid #374151;border-radius:3px;background:transparent;color:#9ca3af;cursor:pointer;font-size:0.8em;">2x</button>
        </div>
      </div>
    </div>
    <script>
    (function() {{
      const signal = {data_json};
      const sampleRate = {sample_rate};
      const totalSamples = signal.length;
      const totalSeconds = totalSamples / sampleRate;
      const peakTimesS = {peaks_json};
      const anomalies = {anomalies_json};
      const windowSamples = {window_samples};
      const windowSec = {window_s};

      const canvas = document.getElementById('ekg-canvas');
      const ctx = canvas.getContext('2d');

      let playing = false;
      let currentSample = {initial_sample} + windowSamples;
      let speed = 1;
      let animFrameId = null;
      let lastTimestamp = null;

      function resizeCanvas() {{
        canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
        canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
      }}
      resizeCanvas();
      window.addEventListener('resize', function() {{ resizeCanvas(); draw(); }});

      const seekContainer = document.getElementById('seekbar-container');
      let seeking = false;
      function seekTo(e) {{
        const rect = seekContainer.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        currentSample = Math.max(windowSamples, pct * totalSamples);
        updateUI(); draw();
      }}
      seekContainer.addEventListener('mousedown', function(e) {{ seeking=true; seekTo(e); }});
      document.addEventListener('mousemove', function(e) {{ if(seeking) seekTo(e); }});
      document.addEventListener('mouseup', function() {{ seeking=false; }});

      function updateUI() {{
        const pct = (currentSample / totalSamples) * 100;
        document.getElementById('seekbar-fill').style.width = pct + '%';
        document.getElementById('seekbar-thumb').style.left = pct + '%';
        const sec = currentSample / sampleRate;
        const min = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        document.getElementById('time-display').textContent = min+':'+(s<10?'0':'')+s+' / {total_time}';

        const hr = computeHR(sec);
        document.getElementById('hr-display').textContent = hr + ' bpm';
      }}

      function computeHR(t) {{
        const ws = 10;
        const s0 = Math.max(0, t - ws);
        let fi=0, li=peakTimesS.length-1;
        for(let i=0;i<peakTimesS.length;i++) {{ if(peakTimesS[i]>=s0){{fi=i;break;}} }}
        for(let i=peakTimesS.length-1;i>=0;i--) {{ if(peakTimesS[i]<=t){{li=i;break;}} }}
        const n = li - fi + 1;
        if(n<2) return '--';
        let tot=0;
        for(let i=fi+1;i<=li;i++) tot += peakTimesS[i]-peakTimesS[i-1];
        const avg = tot/(n-1);
        return avg>0 ? Math.round(60/avg) : '--';
      }}

      function draw() {{
        const w = canvas.width, h = canvas.height;
        const dpr = window.devicePixelRatio || 1;

        ctx.fillStyle = '#111827';
        ctx.fillRect(0,0,w,h);

        ctx.strokeStyle = '#1f2937';
        ctx.lineWidth = 0.5 * dpr;
        for(let i=1;i<8;i++) {{ const y=(h/8)*i; ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke(); }}
        for(let i=1;i<12;i++) {{ const x=(w/12)*i; ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke(); }}

        const startSample = Math.max(0, Math.floor(currentSample - windowSamples));
        const endSample = Math.floor(currentSample);
        const vis = signal.slice(startSample, endSample);
        if(vis.length < 2) return;

        let sMin=Infinity, sMax=-Infinity;
        for(let i=0;i<vis.length;i++) {{ if(vis[i]<sMin)sMin=vis[i]; if(vis[i]>sMax)sMax=vis[i]; }}
        const pad=(sMax-sMin)*0.1||1;
        sMin-=pad; sMax+=pad;
        const range = sMax - sMin;

        const startSec = startSample / sampleRate;
        const endSec = endSample / sampleRate;

        for(let a of anomalies) {{
          if(a.e < startSec || a.s > endSec) continue;
          const x0 = Math.max(0, ((a.s - startSec) / (endSec - startSec)) * w);
          const x1 = Math.min(w, ((a.e - startSec) / (endSec - startSec)) * w);
          ctx.fillStyle = a.c;
          ctx.fillRect(x0, 0, x1 - x0, h);
        }}

        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 1.8 * dpr;
        ctx.lineJoin = 'round';
        ctx.beginPath();
        const step = Math.max(1, Math.floor(vis.length / (w/dpr)));
        for(let i=0;i<vis.length;i+=step) {{
          const x = (i/vis.length)*w;
          const y = h - ((vis[i]-sMin)/range)*h;
          if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        }}
        ctx.stroke();

        for(let pt of peakTimesS) {{
          if(pt < startSec || pt > endSec) continue;
          const x = ((pt - startSec) / (endSec - startSec)) * w;
          const idx = Math.round(pt * sampleRate) - startSample;
          if(idx < 0 || idx >= vis.length) continue;
          const y = h - ((vis[idx]-sMin)/range)*h;
          ctx.fillStyle = '#22c55e';
          ctx.beginPath();
          ctx.moveTo(x, y-6*dpr);
          ctx.lineTo(x-4*dpr, y+2*dpr);
          ctx.lineTo(x+4*dpr, y+2*dpr);
          ctx.closePath();
          ctx.fill();
        }}
      }}

      function animate(ts) {{
        if(!playing) return;
        if(lastTimestamp===null) lastTimestamp=ts;
        const dt = (ts-lastTimestamp)/1000;
        lastTimestamp = ts;
        currentSample += dt * sampleRate * speed;
        if(currentSample >= totalSamples) {{ currentSample = windowSamples; }}
        draw(); updateUI();
        animFrameId = requestAnimationFrame(animate);
      }}

      window.togglePlay = function() {{
        playing = !playing;
        const btn = document.getElementById('btn-play');
        if(playing) {{
          btn.textContent = '⏸ Pause';
          btn.style.background = '#ef4444';
          if(currentSample < windowSamples) currentSample = windowSamples;
          lastTimestamp = null;
          animFrameId = requestAnimationFrame(animate);
        }} else {{
          btn.textContent = '▶ Abspielen';
          btn.style.background = '#3b82f6';
          if(animFrameId) cancelAnimationFrame(animFrameId);
        }}
      }};

      window.resetPlayer = function() {{
        playing = false;
        currentSample = {initial_sample} + windowSamples;
        if(currentSample > totalSamples) currentSample = windowSamples;
        document.getElementById('btn-play').textContent = '▶ Abspielen';
        document.getElementById('btn-play').style.background = '#3b82f6';
        if(animFrameId) cancelAnimationFrame(animFrameId);
        updateUI(); draw();
      }};

      window.setSpeed = function(s) {{
        speed = s;
        document.querySelectorAll('.spd-btn').forEach(function(b) {{
          if(parseFloat(b.dataset.speed) === s) {{
            b.style.border = '1px solid #3b82f6';
            b.style.color = '#3b82f6';
            b.style.background = 'rgba(59,130,246,0.15)';
          }} else {{
            b.style.border = '1px solid #374151';
            b.style.color = '#9ca3af';
            b.style.background = 'transparent';
          }}
        }});
      }};

      draw(); updateUI();
    }})();
    </script>
    """

    components.html(html, height=430)


# ── Aktivitäten Tab (Platzhalter) ──

def show_activities(person):
    st.markdown("##### Aktivitäten & GPX-Tracks")
    st.info(
        "Hier werden zukünftig Trainings-Aktivitäten und GPS-Tracks angezeigt.\n\n"
        "- Lauf-/Radtouren mit Karte\n"
        "- Herzfrequenz-Zonen\n"
        "- Trainingsstatistiken"
    )


# ── EKG + Tabs anzeigen ──

def show_data_for_person(person):
    tab_analyse, tab_activities = st.tabs(
        ["📊 EKG-Analyse", "🏃 Aktivitäten"]
    )

    with tab_activities:
        show_activities(person)

    if not person.ekg_tests:
        with tab_analyse:
            st.info("Keine EKG-Daten vorhanden.")
        return

    def _infer_test_type(t):
        rl = (t.get("result_link") or "").lower()
        if "belast" in rl or "stress" in rl:
            return "Belastungs-EKG"
        if "ruhe" in rl or "rest" in rl:
            return "Ruhe-EKG"
        return t.get("type") or "EKG-Test"

    if len(person.ekg_tests) == 1:
        test_id = person.ekg_tests[0]["id"]
        with tab_analyse:
            ekg = db.find_ekg_by_id(test_id, person.id)
            if ekg is None:
                st.error("EKG-Daten konnten nicht geladen werden.")
            else:
                show_ekg_analyse(ekg, person=person)
    else:
        test_options = {}
        for t in person.ekg_tests:
            label = f"{_infer_test_type(t)} — {t.get('date')}"
            test_options[label] = t["id"]

        with tab_analyse:
            selected_test = st.selectbox(
                "EKG-Test auswählen",
                options=test_options.keys(),
                key=f"ekg_select_analyse_{person.id}",
            )
            test_id = test_options[selected_test]
            ekg = db.find_ekg_by_id(test_id, person.id)
            if ekg is None:
                st.error("EKG-Daten konnten nicht geladen werden.")
            else:
                show_ekg_analyse(ekg, person=person)


# ── Arzt-Dashboard ──

def show_doctor_dashboard():
    st.title("CardioConnect — Arzt-Dashboard")

    person_names = db.get_person_list()
    if not person_names:
        st.warning("Keine Patienten in der Datenbank.")
        return

    st.sidebar.divider()
    selected_name = st.sidebar.selectbox("Patient auswählen", options=person_names)
    person_dict = db.find_person_data_by_name(selected_name)

    if person_dict is None:
        st.error("Patient nicht gefunden.")
        return

    person = Person(person_dict)
    show_patient_header(person)
    st.divider()
    show_data_for_person(person)


# ── Patienten-Verwaltung ──

def show_verwaltung():
    st.title("CardioConnect — Patientenverwaltung")

    edit_id = st.session_state.edit_person_id

    if edit_id == "new":
        _show_new_patient_form()
        return

    if edit_id is not None:
        _show_edit_patient(edit_id)
        return

    _show_patient_list()


def _show_patient_list():
    persons = db.get_all_persons()

    col_header, col_btn = st.columns([3, 1])
    with col_header:
        st.subheader("Alle Patienten")
    with col_btn:
        if st.button("＋ Neuer Patient", width="stretch", type="primary"):
            st.session_state.edit_person_id = "new"
            st.rerun()

    if not persons:
        st.info("Noch keine Patienten angelegt.")
        return

    for p in persons:
        person = Person(p | {"ekg_tests": db.get_ekg_tests_for_person(p["id"])})
        ekg_count = len(person.ekg_tests)

        with st.container(border=True):
            c_img, c_info, c_stats, c_actions = st.columns([1, 4, 2, 2])

            with c_img:
                st.image(person.picture_path, width=70)

            with c_info:
                st.markdown(f"**{person.firstname} {person.lastname}**")
                parts = [f"Geb. {person.format_birth_date()}"]
                parts.append(f"{person.calc_age()} J.")
                parts.append("Männlich" if person.gender == "male" else "Weiblich")
                if person.height_cm:
                    parts.append(f"{int(person.height_cm)} cm")
                if person.weight_kg:
                    parts.append(f"{person.weight_kg} kg")
                st.caption(" · ".join(parts))

            with c_stats:
                st.metric("EKG-Tests", ekg_count)

            with c_actions:
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("Bearbeiten", key=f"edit_{p['id']}",
                                 width="stretch"):
                        st.session_state.edit_person_id = p["id"]
                        st.rerun()
                with bc2:
                    if st.button("Löschen", key=f"del_{p['id']}",
                                 width="stretch"):
                        st.session_state[f"confirm_delete_{p['id']}"] = True
                        st.rerun()

            if st.session_state.get(f"confirm_delete_{p['id']}"):
                st.warning(
                    f"**{person.firstname} {person.lastname}** wirklich löschen? "
                    "Alle EKG-Tests werden ebenfalls entfernt."
                )
                dc1, dc2, dc3 = st.columns([1, 1, 4])
                with dc1:
                    if st.button("Ja, löschen", key=f"confirm_yes_{p['id']}",
                                 type="primary"):
                        db.delete_person(p["id"])
                        st.session_state.pop(f"confirm_delete_{p['id']}", None)
                        st.rerun()
                with dc2:
                    if st.button("Abbrechen", key=f"confirm_no_{p['id']}"):
                        st.session_state.pop(f"confirm_delete_{p['id']}", None)
                        st.rerun()


def _show_new_patient_form():
    if st.button("← Zurück zur Übersicht"):
        st.session_state.edit_person_id = None
        st.rerun()

    st.subheader("Neuen Patienten anlegen")

    with st.form("new_patient_form"):
        st.markdown("**Persönliche Daten**")
        c1, c2 = st.columns(2)
        with c1:
            firstname = st.text_input("Vorname *")
        with c2:
            lastname = st.text_input("Nachname *")

        c3, c4 = st.columns(2)
        with c3:
            birth_date = st.date_input(
                "Geburtsdatum *",
                value=date(1990, 1, 1),
                min_value=date(1900, 1, 1),
                max_value=date.today(),
            )
        with c4:
            gender = st.selectbox("Geschlecht", ["male", "female"],
                                  format_func=lambda g: "Männlich" if g == "male"
                                  else "Weiblich")

        st.markdown("**Körperdaten** (optional)")
        c5, c6, c7 = st.columns(3)
        with c5:
            height_cm = st.number_input("Größe (cm)", min_value=0, max_value=250,
                                        value=0, step=1)
        with c6:
            weight_kg = st.number_input("Gewicht (kg)", min_value=0.0, max_value=300.0,
                                        value=0.0, step=0.5)
        with c7:
            body_fat = st.number_input("Körperfett (%)", min_value=0.0, max_value=60.0,
                                       value=0.0, step=0.5)

        picture = st.file_uploader("Profilbild (optional)", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("Patient anlegen", type="primary")

    if submitted:
        if not firstname.strip() or not lastname.strip():
            st.error("Vor- und Nachname sind Pflichtfelder.")
            return

        dob_str = birth_date.isoformat()
        h = height_cm if height_cm > 0 else None
        w = weight_kg if weight_kg > 0 else None
        bf = body_fat if body_fat > 0 else None

        person_id = db.add_person(
            firstname.strip(), lastname.strip(), dob_str, gender,
            height_cm=h, weight_kg=w, body_fat_pct=bf,
        )

        if picture is not None:
            pic_path = db.save_uploaded_picture(picture, person_id)
            db.update_person(person_id, firstname.strip(), lastname.strip(),
                             dob_str, gender, picture_path=pic_path,
                             height_cm=h, weight_kg=w, body_fat_pct=bf)

        st.success(f"**{firstname} {lastname}** wurde angelegt.")
        st.session_state.edit_person_id = person_id
        st.rerun()


def _show_edit_patient(person_id):
    person_dict = db.get_person_by_id(person_id)
    if person_dict is None:
        st.error("Patient nicht gefunden.")
        st.session_state.edit_person_id = None
        return

    person = Person(person_dict)

    if st.button("← Zurück zur Übersicht"):
        st.session_state.edit_person_id = None
        st.rerun()

    st.subheader(f"{person.firstname} {person.lastname}")

    # ── Profildaten ──

    with st.container(border=True):
        c_img, c_form = st.columns([1, 4])
        with c_img:
            st.image(person.picture_path, width=140)

        with c_form:
            with st.form("edit_patient_form"):
                st.markdown("**Persönliche Daten**")
                c1, c2 = st.columns(2)
                with c1:
                    firstname = st.text_input("Vorname", value=person.firstname)
                with c2:
                    lastname = st.text_input("Nachname", value=person.lastname)

                c3, c4 = st.columns(2)
                with c3:
                    bd = person.get_birth_date() or date(1990, 1, 1)
                    birth_date = st.date_input(
                        "Geburtsdatum", value=bd,
                        min_value=date(1900, 1, 1),
                        max_value=date.today(),
                    )
                with c4:
                    gender_options = ["male", "female"]
                    gender_idx = gender_options.index(person.gender) \
                        if person.gender in gender_options else 0
                    gender = st.selectbox(
                        "Geschlecht", gender_options,
                        index=gender_idx,
                        format_func=lambda g: "Männlich" if g == "male"
                        else "Weiblich",
                    )

                st.markdown("**Körperdaten**")
                c5, c6, c7 = st.columns(3)
                with c5:
                    height_cm = st.number_input(
                        "Größe (cm)", min_value=0, max_value=250,
                        value=int(person.height_cm or 0), step=1,
                    )
                with c6:
                    weight_kg = st.number_input(
                        "Gewicht (kg)", min_value=0.0, max_value=300.0,
                        value=float(person.weight_kg or 0), step=0.5,
                    )
                with c7:
                    body_fat = st.number_input(
                        "Körperfett (%)", min_value=0.0, max_value=60.0,
                        value=float(person.body_fat_pct or 0), step=0.5,
                    )

                new_picture = st.file_uploader(
                    "Neues Profilbild", type=["jpg", "jpeg", "png"],
                )

                submitted = st.form_submit_button("Änderungen speichern",
                                                  type="primary")

            if submitted:
                if not firstname.strip() or not lastname.strip():
                    st.error("Vor- und Nachname sind Pflichtfelder.")
                else:
                    pic_path = None
                    if new_picture is not None:
                        pic_path = db.save_uploaded_picture(new_picture, person_id)

                    dob_str = birth_date.isoformat()
                    h = height_cm if height_cm > 0 else None
                    w = weight_kg if weight_kg > 0 else None
                    bf = body_fat if body_fat > 0 else None

                    db.update_person(
                        person_id, firstname.strip(), lastname.strip(),
                        dob_str, gender, picture_path=pic_path,
                        height_cm=h, weight_kg=w, body_fat_pct=bf,
                    )
                    st.success("Änderungen gespeichert.")
                    st.rerun()

    # ── EKG-Tests ──

    st.divider()
    _show_ekg_management(person_id)


def _show_ekg_management(person_id):
    st.markdown("##### EKG-Tests")

    tests = db.get_ekg_tests_for_person(person_id)

    if tests:
        for t in tests:
            with st.container(border=True):
                tc1, tc2, tc3 = st.columns([2, 4, 1])
                with tc1:
                    st.markdown(f"**Test #{t['id']}**")
                    st.caption(f"Datum: {t['date']}")
                with tc2:
                    st.caption(f"`{t['result_link']}`")
                with tc3:
                    if st.button("Entfernen", key=f"del_ekg_{t['id']}"):
                        db.delete_ekg_test(t["id"])
                        st.rerun()
    else:
        st.info("Noch keine EKG-Tests vorhanden.")

    st.markdown("")

    with st.expander("Neuen EKG-Test hochladen"):
        with st.form("upload_ekg_form"):
            ekg_file = st.file_uploader(
                "EKG-Datei (.csv oder .txt)",
                type=["csv", "txt"],
            )
            ekg_date = st.date_input("Aufnahmedatum", value=date.today())
            upload_submitted = st.form_submit_button(
                "Hochladen", type="primary",
            )

        if upload_submitted:
            if ekg_file is None:
                st.error("Bitte eine EKG-Datei auswählen.")
            else:
                result_link = db.save_uploaded_ekg(ekg_file, person_id)
                date_str = ekg_date.strftime("%d.%m.%Y")
                db.add_ekg_test(person_id, date_str, result_link)
                st.success(f"EKG-Test vom {date_str} wurde hinzugefügt.")
                st.rerun()


# ── Patienten-Ansicht ──

def show_patient_view():
    st.title("CardioConnect — Meine Daten")

    user = st.session_state.user
    person_dict = db.get_person_by_id(user["person_id"])

    if person_dict is None:
        st.error("Kein Patientenprofil verknüpft. Bitte den Arzt kontaktieren.")
        return

    person = Person(person_dict)
    show_patient_header(person)
    st.divider()
    show_data_for_person(person)


# ── Routing ──

if st.session_state.user is None:
    show_login()
else:
    show_sidebar_user_info()

    if st.session_state.user["role"] == "doctor":
        show_sidebar_nav()

        if st.session_state.doctor_page == "dashboard":
            show_doctor_dashboard()
        else:
            show_verwaltung()
    else:
        show_sidebar_patient()
        show_patient_view()
