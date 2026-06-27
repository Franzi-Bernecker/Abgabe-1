import json

import streamlit as st
import streamlit.components.v1 as components

import database as db
from person import Person
from datetime import date


# Fallbacks: falls die geladene `Person`-Klasse bestimmte Helfer nicht hat,
# ergänzen wir sie zur Laufzeit (vermeidet AttributeError bei unterschiedlichen Modulen).
if not hasattr(Person, "get_birth_year"):
    def _get_birth_year(self):
        dob = getattr(self, "date_of_birth", None)
        if isinstance(dob, int):
            return dob
        try:
            return date.fromisoformat(dob).year
        except Exception:
            try:
                return int(str(dob).split("-")[0])
            except Exception:
                return None

    Person.get_birth_year = _get_birth_year

if not hasattr(Person, "calc_age"):
    def _calc_age(self):
        try:
            by = self.get_birth_year()
            return date.today().year - (by or date.today().year)
        except Exception:
            return 0

    Person.calc_age = _calc_age


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


# ── EKG Analyse Tab ──

def show_ekg_analyse(ekg):
    total_s = ekg.duration_s

    st.caption(f"Aufnahmedauer: {total_s:.1f} s ({total_s/60:.1f} min) | Abtastrate: {ekg.SAMPLE_RATE} Hz")

    st.markdown("##### Übersicht")
    st.plotly_chart(ekg.plot_overview(), width="stretch", key=f"overview_{ekg.id}")

    st.markdown("##### Detailansicht")

    col_window, col_start = st.columns([1, 3])
    with col_window:
        window_s = st.select_slider(
            "Fenster (s)",
            options=[5, 10, 15, 20, 30, 60],
            value=10,
            key=f"window_{ekg.id}",
        )
    with col_start:
        max_start = max(0.0, total_s - window_s)
        start_s = st.slider(
            "Startzeit (s)",
            min_value=0.0,
            max_value=max_start,
            value=0.0,
            step=0.5,
            key=f"start_{ekg.id}",
        )

    end_s = start_s + window_s

    col_hr, col_peaks, col_range = st.columns(3)
    hr_window = ekg.estimate_hr(start_s, end_s)
    peaks_in_window = len(ekg.get_peaks_in_range(start_s, end_s))

    with col_hr:
        st.metric("HR (Fenster)", f"{hr_window} bpm")
    with col_peaks:
        st.metric("Herzschläge (Fenster)", str(peaks_in_window))
    with col_range:
        st.metric("HR (gesamt)", f"{ekg.heart_rate} bpm")

    st.plotly_chart(ekg.plot_detail(start_s, end_s), width="stretch", key=f"detail_{ekg.id}")

    hr_fig = ekg.plot_hr_trend()
    if hr_fig:
        st.markdown("##### Herzfrequenz-Verlauf")
        st.plotly_chart(hr_fig, width="stretch", key=f"hr_trend_{ekg.id}")


# ── EKG Monitor Tab (Client-side Canvas Animation) ──

def show_ekg_monitor(ekg):
    signal = ekg.df[ekg.signal_col].values.tolist()
    sample_rate = ekg.SAMPLE_RATE

    if ekg.peaks is None:
        ekg.find_peaks()
    peak_times_s = (ekg.df["Zeit in s"].iloc[ekg.peaks].values).tolist()

    data_json = json.dumps(signal)
    peaks_json = json.dumps(peak_times_s)

    html = f"""
    <div id="monitor-container" style="background:#1a1a2e;border-radius:8px;padding:16px;font-family:monospace;">
      <div style="text-align:center;margin-bottom:8px;">
        <span id="hr-display" style="font-size:2.2em;color:#00ff41;">♥ -- bpm</span>
      </div>
      <canvas id="ekg-canvas" style="width:100%;height:280px;display:block;"></canvas>
      <div style="margin-top:10px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span id="time-current" style="color:#aaa;font-size:0.75em;min-width:45px;">0:00</span>
          <div id="seekbar-container" style="flex:1;height:20px;cursor:pointer;position:relative;display:flex;align-items:center;">
            <div style="width:100%;height:6px;background:#2d2d44;border-radius:3px;position:relative;">
              <div id="seekbar-fill" style="height:100%;width:0%;background:#00ff41;border-radius:3px;transition:width 0.1s;"></div>
              <div id="seekbar-thumb" style="position:absolute;top:50%;left:0%;transform:translate(-50%,-50%);width:14px;height:14px;background:#00ff41;border-radius:50%;box-shadow:0 0 4px rgba(0,255,65,0.5);"></div>
            </div>
          </div>
          <span id="time-total" style="color:#666;font-size:0.75em;min-width:45px;text-align:right;">{int(ekg.duration_s // 60)}:{int(ekg.duration_s % 60):02d}</span>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:10px;flex-wrap:wrap;">
        <button id="btn-play" onclick="togglePlay()" style="padding:8px 20px;border:none;border-radius:4px;background:#00ff41;color:#1a1a2e;font-weight:bold;cursor:pointer;font-size:1em;">▶ Start</button>
        <button onclick="resetMonitor()" style="padding:8px 20px;border:none;border-radius:4px;background:#444;color:#fff;cursor:pointer;font-size:1em;">⏮ Reset</button>
        <label style="color:#aaa;font-size:0.85em;">Speed:
          <input id="speed-input" type="range" min="0.5" max="10" step="0.5" value="3" style="width:100px;vertical-align:middle;">
          <span id="speed-label" style="color:#00ff41;">3x</span>
        </label>
        <label style="color:#aaa;font-size:0.85em;">Fenster:
          <select id="window-select" style="background:#333;color:#fff;border:1px solid #555;border-radius:3px;padding:2px 6px;">
            <option value="4">4s</option>
            <option value="6" selected>6s</option>
            <option value="8">8s</option>
            <option value="10">10s</option>
          </select>
        </label>
      </div>
    </div>
    <script>
    (function() {{
      const signal = {data_json};
      const sampleRate = {sample_rate};
      const totalSamples = signal.length;
      const totalSeconds = totalSamples / sampleRate;
      const peakTimesS = {peaks_json};

      const canvas = document.getElementById('ekg-canvas');
      const ctx = canvas.getContext('2d');

      let playing = false;
      let currentSample = 0;
      let animFrameId = null;
      let lastTimestamp = null;

      function getSpeed() {{
        return parseFloat(document.getElementById('speed-input').value);
      }}
      function getWindowSec() {{
        return parseInt(document.getElementById('window-select').value);
      }}

      document.getElementById('speed-input').addEventListener('input', function() {{
        document.getElementById('speed-label').textContent = this.value + 'x';
      }});

      const seekContainer = document.getElementById('seekbar-container');
      let seeking = false;

      function seekToPosition(e) {{
        const rect = seekContainer.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        currentSample = pct * totalSamples;
        updateSeekbar();
        draw();
        const hr = computeHR(currentSample / sampleRate);
        document.getElementById('hr-display').textContent = '♥ ' + hr + ' bpm';
      }}

      seekContainer.addEventListener('mousedown', function(e) {{
        seeking = true;
        seekToPosition(e);
      }});
      document.addEventListener('mousemove', function(e) {{
        if (seeking) seekToPosition(e);
      }});
      document.addEventListener('mouseup', function() {{
        seeking = false;
      }});
      seekContainer.addEventListener('touchstart', function(e) {{
        seeking = true;
        seekToPosition(e.touches[0]);
      }});
      document.addEventListener('touchmove', function(e) {{
        if (seeking) seekToPosition(e.touches[0]);
      }});
      document.addEventListener('touchend', function() {{
        seeking = false;
      }});

      function updateSeekbar() {{
        const pct = (currentSample / totalSamples) * 100;
        document.getElementById('seekbar-fill').style.width = pct + '%';
        document.getElementById('seekbar-thumb').style.left = pct + '%';
        const sec = currentSample / sampleRate;
        const min = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        document.getElementById('time-current').textContent = min + ':' + (s < 10 ? '0' : '') + s;
      }}

      function resizeCanvas() {{
        canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
        canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
      }}
      resizeCanvas();
      window.addEventListener('resize', resizeCanvas);

      function computeHR(currentTimeSec) {{
        const windowSec = 10;
        const startSec = Math.max(0, currentTimeSec - windowSec);
        let firstIdx = 0;
        let lastIdx = peakTimesS.length - 1;
        for (let i = 0; i < peakTimesS.length; i++) {{
          if (peakTimesS[i] >= startSec) {{ firstIdx = i; break; }}
        }}
        for (let i = peakTimesS.length - 1; i >= 0; i--) {{
          if (peakTimesS[i] <= currentTimeSec) {{ lastIdx = i; break; }}
        }}
        const peaksInWindow = lastIdx - firstIdx + 1;
        if (peaksInWindow < 2) return '--';

        let totalInterval = 0;
        for (let i = firstIdx + 1; i <= lastIdx; i++) {{
          totalInterval += peakTimesS[i] - peakTimesS[i-1];
        }}
        const avgInterval = totalInterval / (peaksInWindow - 1);
        if (avgInterval <= 0) return '--';
        return Math.round(60 / avgInterval);
      }}

      function draw() {{
        const w = canvas.width;
        const h = canvas.height;
        const dpr = window.devicePixelRatio || 1;
        const windowSec = getWindowSec();
        const windowSamples = windowSec * sampleRate;

        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, w, h);

        // Grid
        ctx.strokeStyle = '#2d2d44';
        ctx.lineWidth = 0.5 * dpr;
        const gridLines = 8;
        for (let i = 1; i < gridLines; i++) {{
          const y = (h / gridLines) * i;
          ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
        }}
        for (let i = 1; i < 12; i++) {{
          const x = (w / 12) * i;
          ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
        }}

        // Signal
        const startSample = Math.max(0, Math.floor(currentSample - windowSamples));
        const endSample = Math.floor(currentSample);
        const visibleSignal = signal.slice(startSample, endSample);

        if (visibleSignal.length < 2) return;

        let sigMin = Infinity, sigMax = -Infinity;
        for (let i = 0; i < visibleSignal.length; i++) {{
          if (visibleSignal[i] < sigMin) sigMin = visibleSignal[i];
          if (visibleSignal[i] > sigMax) sigMax = visibleSignal[i];
        }}
        const padding = (sigMax - sigMin) * 0.1 || 1;
        sigMin -= padding;
        sigMax += padding;

        ctx.strokeStyle = '#00ff41';
        ctx.lineWidth = 1.8 * dpr;
        ctx.lineJoin = 'round';
        ctx.beginPath();

        const samplesPerPixel = visibleSignal.length / (w / dpr);
        const pixelStep = Math.max(1, Math.floor(samplesPerPixel));

        for (let i = 0; i < visibleSignal.length; i += pixelStep) {{
          const x = (i / visibleSignal.length) * w;
          const y = h - ((visibleSignal[i] - sigMin) / (sigMax - sigMin)) * h;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }}
        ctx.stroke();
      }}

      function animate(timestamp) {{
        if (!playing) return;
        if (lastTimestamp === null) lastTimestamp = timestamp;

        const dt = (timestamp - lastTimestamp) / 1000;
        lastTimestamp = timestamp;

        const speed = getSpeed();
        currentSample += dt * sampleRate * speed;

        if (currentSample >= totalSamples) {{
          currentSample = getWindowSec() * sampleRate;
        }}

        draw();

        const hr = computeHR(currentSample / sampleRate);
        document.getElementById('hr-display').textContent = '♥ ' + hr + ' bpm';
        updateSeekbar();

        animFrameId = requestAnimationFrame(animate);
      }}

      window.togglePlay = function() {{
        playing = !playing;
        const btn = document.getElementById('btn-play');
        if (playing) {{
          btn.textContent = '⏸ Pause';
          btn.style.background = '#ff6b35';
          if (currentSample < getWindowSec() * sampleRate) {{
            currentSample = getWindowSec() * sampleRate;
          }}
          lastTimestamp = null;
          animFrameId = requestAnimationFrame(animate);
        }} else {{
          btn.textContent = '▶ Start';
          btn.style.background = '#00ff41';
          if (animFrameId) cancelAnimationFrame(animFrameId);
        }}
      }};

      window.resetMonitor = function() {{
        playing = false;
        currentSample = 0;
        document.getElementById('btn-play').textContent = '▶ Start';
        document.getElementById('btn-play').style.background = '#00ff41';
        document.getElementById('hr-display').textContent = '♥ -- bpm';
        if (animFrameId) cancelAnimationFrame(animFrameId);
        updateSeekbar();
        draw();
      }};

      draw();
    }})();
    </script>
    """

    components.html(html, height=450)


# ── Aktivitäten Tab (Platzhalter) ──

def show_activities(person):
    st.markdown("##### Aktivitäten & GPX-Tracks")
    st.info(
        "Hier werden zukünftig Trainings-Aktivitäten und GPS-Tracks angezeigt.\n\n"
        "- Lauf-/Radtouren mit Karte\n"
        "- Herzfrequenz-Zonen\n"
        "- Trainingsstatistiken"
    )


# ── EKG + Tabs anzeigen (wird von beiden Ansichten benutzt) ──

def show_data_for_person(person):
    tab_analyse, tab_monitor, tab_activities = st.tabs(
        ["📊 EKG-Analyse", "🖥️ Live-Monitor", "🏃 Aktivitäten"]
    )

    with tab_activities:
        show_activities(person)

    if not person.ekg_tests:
        with tab_analyse:
            st.info("Keine EKG-Daten vorhanden.")
        with tab_monitor:
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
                show_ekg_analyse(ekg)
        with tab_monitor:
            ekg_mon = db.find_ekg_by_id(test_id, person.id)
            if ekg_mon is None:
                st.error("EKG-Daten konnten nicht geladen werden.")
            else:
                show_ekg_monitor(ekg_mon)
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
                show_ekg_analyse(ekg)

        with tab_monitor:
            selected_test_mon = st.selectbox(
                "EKG-Test auswählen",
                options=test_options.keys(),
                key=f"ekg_select_monitor_{person.id}",
            )
            test_id_mon = test_options[selected_test_mon]
            ekg_mon = db.find_ekg_by_id(test_id_mon, person.id)
            if ekg_mon is None:
                st.error("EKG-Daten konnten nicht geladen werden.")
            else:
                show_ekg_monitor(ekg_mon)


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
        st.metric("Geburtsjahr", person.get_birth_year())
        st.metric("Alter", f"{person.calc_age()} Jahre")
        st.metric("Max. Herzfrequenz", f"{person.calc_max_heart_rate()} bpm")

    st.divider()
    show_data_for_person(person)


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
        st.metric("Geburtsjahr", person.get_birth_year())
        st.metric("Alter", f"{person.calc_age()} Jahre")
        st.metric("Max. Herzfrequenz", f"{person.calc_max_heart_rate()} bpm")

    st.divider()
    show_data_for_person(person)


# ── Routing ──

if st.session_state.user is None:
    show_login()
else:
    show_sidebar_user_info()

    if st.session_state.user["role"] == "doctor":
        show_doctor_view()
    else:
        show_patient_view()
