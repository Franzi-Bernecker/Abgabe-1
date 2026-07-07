"""Live-EKG-Monitor: Canvas-Player im Stil eines Krankenhausmonitors.

Der Player ist bewusst als HTML/JS-Canvas umgesetzt: nur so ist eine flüssige
Echtzeit-Wiedergabe (60 fps) mit Abspielgeschwindigkeit und Seekbar möglich.
Das Markup wird aus einem ``string.Template`` erzeugt; die Signaldaten werden
einmal pro Datei als JSON aufbereitet und gecacht.
"""

import json
from string import Template

import streamlit as st

from cardioconnect.config import EKG_SAMPLE_RATE
from cardioconnect.models.ekg import EKG, analyze, load_signal

_FILL = {
    "pause": "rgba(208, 59, 59, 0.30)",
    "irregular": "rgba(250, 178, 25, 0.25)",
    "tachycardia": "rgba(236, 131, 90, 0.22)",
    "bradycardia": "rgba(42, 120, 214, 0.20)",
}


@st.cache_data(show_spinner=False)
def _payload(file_path: str) -> dict:
    """JSON strings for the player, built once per EKG file."""
    signal = load_signal(file_path)["signal"].round(3).tolist()
    analysis = analyze(file_path)
    regions = [
        {
            "s": ep["start_s"],
            "e": ep["end_s"],
            "c": _FILL[ep["type"]],
        }
        for ep in analysis["episodes"]
    ]
    return {
        "signal_json": json.dumps(signal),
        "peaks_json": json.dumps(analysis["peak_times_s"].round(3).tolist()),
        "anomalies_json": json.dumps(regions),
    }


def render(ekg: EKG, initial_start_s: float = 0.0, window_s: float = 10.0) -> None:
    payload = _payload(ekg.file_path)
    total_s = ekg.duration_s
    total_time = f"{int(total_s // 60)}:{int(total_s % 60):02d}"

    html = _TEMPLATE.substitute(
        signal_json=payload["signal_json"],
        peaks_json=payload["peaks_json"],
        anomalies_json=payload["anomalies_json"],
        sample_rate=EKG_SAMPLE_RATE,
        initial_sample=int(initial_start_s * EKG_SAMPLE_RATE),
        window_samples=max(1, int(window_s * EKG_SAMPLE_RATE)),
        total_time=total_time,
    )
    st.iframe(html, height=440)


_TEMPLATE = Template("""
<div style="background:#111827;border-radius:8px;padding:16px;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <span id="hr-display" style="font-size:1.6em;color:#00ff41;font-family:monospace;font-weight:700;">-- bpm</span>
    <span id="time-display" style="font-size:0.85em;color:#6b7280;font-family:monospace;">0:00 / $total_time</span>
  </div>
  <canvas id="ekg-canvas" style="width:100%;height:300px;display:block;border-radius:4px;"></canvas>
  <div id="seekbar" style="margin-top:10px;height:20px;cursor:pointer;display:flex;align-items:center;">
    <div style="width:100%;height:4px;background:#1f2937;border-radius:2px;position:relative;">
      <div id="seek-fill" style="height:100%;width:0%;background:#3b82f6;border-radius:2px;"></div>
      <div id="seek-thumb" style="position:absolute;top:50%;left:0%;transform:translate(-50%,-50%);width:12px;height:12px;background:#3b82f6;border-radius:50%;"></div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;margin-top:10px;">
    <button id="btn-play" style="padding:6px 16px;border:none;border-radius:4px;background:#3b82f6;color:#fff;font-weight:600;cursor:pointer;font-size:0.85em;">&#9654; Abspielen</button>
    <button id="btn-reset" style="padding:6px 16px;border:none;border-radius:4px;background:#374151;color:#9ca3af;cursor:pointer;font-size:0.85em;">&#9198; Reset</button>
    <div id="speed-buttons" style="display:flex;gap:4px;margin-left:8px;"></div>
  </div>
</div>
<script>
(function() {
  var signal = $signal_json;
  var peakTimes = $peaks_json;
  var anomalies = $anomalies_json;
  var sampleRate = $sample_rate;
  var windowSamples = $window_samples;
  var initialSample = $initial_sample;
  var totalSamples = signal.length;

  var canvas = document.getElementById('ekg-canvas');
  var ctx = canvas.getContext('2d');
  var playing = false;
  var speed = 1;
  var currentSample = Math.min(totalSamples, initialSample + windowSamples);
  var animId = null;
  var lastTs = null;

  function resize() {
    var dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = canvas.offsetHeight * dpr;
  }
  resize();
  window.addEventListener('resize', function() { resize(); draw(); });

  function computeHR(t) {
    var s0 = Math.max(0, t - 10);
    var inWin = [];
    for (var i = 0; i < peakTimes.length; i++) {
      if (peakTimes[i] >= s0 && peakTimes[i] <= t) inWin.push(peakTimes[i]);
    }
    if (inWin.length < 2) return '--';
    var avg = (inWin[inWin.length - 1] - inWin[0]) / (inWin.length - 1);
    return avg > 0 ? Math.round(60 / avg) : '--';
  }

  function updateUI() {
    var pct = (currentSample / totalSamples) * 100;
    document.getElementById('seek-fill').style.width = pct + '%';
    document.getElementById('seek-thumb').style.left = pct + '%';
    var sec = currentSample / sampleRate;
    var m = Math.floor(sec / 60);
    var s = Math.floor(sec % 60);
    document.getElementById('time-display').textContent =
      m + ':' + (s < 10 ? '0' : '') + s + ' / $total_time';
    document.getElementById('hr-display').textContent = computeHR(sec) + ' bpm';
  }

  function draw() {
    var w = canvas.width, h = canvas.height;
    var dpr = window.devicePixelRatio || 1;
    ctx.fillStyle = '#111827';
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = '#1f2937';
    ctx.lineWidth = 0.5 * dpr;
    for (var i = 1; i < 8; i++) {
      var y = (h / 8) * i;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
    for (var j = 1; j < 12; j++) {
      var x = (w / 12) * j;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }

    var startSample = Math.max(0, Math.floor(currentSample - windowSamples));
    var endSample = Math.floor(currentSample);
    var vis = signal.slice(startSample, endSample);
    if (vis.length < 2) return;

    var sMin = Infinity, sMax = -Infinity;
    for (var k = 0; k < vis.length; k++) {
      if (vis[k] < sMin) sMin = vis[k];
      if (vis[k] > sMax) sMax = vis[k];
    }
    var pad = (sMax - sMin) * 0.1 || 1;
    sMin -= pad; sMax += pad;
    var range = sMax - sMin;
    var startSec = startSample / sampleRate;
    var endSec = endSample / sampleRate;

    for (var a = 0; a < anomalies.length; a++) {
      var an = anomalies[a];
      if (an.e < startSec || an.s > endSec) continue;
      var x0 = Math.max(0, ((an.s - startSec) / (endSec - startSec)) * w);
      var x1 = Math.min(w, ((an.e - startSec) / (endSec - startSec)) * w);
      ctx.fillStyle = an.c;
      ctx.fillRect(x0, 0, x1 - x0, h);
    }

    ctx.strokeStyle = '#00ff41';
    ctx.lineWidth = 1.8 * dpr;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    var step = Math.max(1, Math.floor(vis.length / (w / dpr)));
    for (var p = 0; p < vis.length; p += step) {
      var px = (p / vis.length) * w;
      var py = h - ((vis[p] - sMin) / range) * h;
      if (p === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();

    ctx.fillStyle = '#22c55e';
    for (var q = 0; q < peakTimes.length; q++) {
      var pt = peakTimes[q];
      if (pt < startSec || pt > endSec) continue;
      var idx = Math.round(pt * sampleRate) - startSample;
      if (idx < 0 || idx >= vis.length) continue;
      var mx = ((pt - startSec) / (endSec - startSec)) * w;
      var my = h - ((vis[idx] - sMin) / range) * h;
      ctx.beginPath();
      ctx.moveTo(mx, my - 6 * dpr);
      ctx.lineTo(mx - 4 * dpr, my + 2 * dpr);
      ctx.lineTo(mx + 4 * dpr, my + 2 * dpr);
      ctx.closePath();
      ctx.fill();
    }
  }

  function animate(ts) {
    if (!playing) return;
    if (lastTs === null) lastTs = ts;
    currentSample += ((ts - lastTs) / 1000) * sampleRate * speed;
    lastTs = ts;
    if (currentSample >= totalSamples) currentSample = windowSamples;
    draw(); updateUI();
    animId = requestAnimationFrame(animate);
  }

  var btnPlay = document.getElementById('btn-play');
  btnPlay.addEventListener('click', function() {
    playing = !playing;
    if (playing) {
      btnPlay.innerHTML = '&#9208; Pause';
      btnPlay.style.background = '#ef4444';
      lastTs = null;
      animId = requestAnimationFrame(animate);
    } else {
      btnPlay.innerHTML = '&#9654; Abspielen';
      btnPlay.style.background = '#3b82f6';
      if (animId) cancelAnimationFrame(animId);
    }
  });

  document.getElementById('btn-reset').addEventListener('click', function() {
    playing = false;
    currentSample = Math.min(totalSamples, initialSample + windowSamples);
    btnPlay.innerHTML = '&#9654; Abspielen';
    btnPlay.style.background = '#3b82f6';
    if (animId) cancelAnimationFrame(animId);
    updateUI(); draw();
  });

  var speedBox = document.getElementById('speed-buttons');
  [0.5, 1, 2].forEach(function(s) {
    var b = document.createElement('button');
    b.textContent = s + 'x';
    b.style.cssText = 'padding:4px 10px;border-radius:3px;cursor:pointer;font-size:0.8em;';
    function style(active) {
      b.style.border = active ? '1px solid #3b82f6' : '1px solid #374151';
      b.style.color = active ? '#3b82f6' : '#9ca3af';
      b.style.background = active ? 'rgba(59,130,246,0.15)' : 'transparent';
    }
    style(s === 1);
    b.addEventListener('click', function() {
      speed = s;
      Array.prototype.forEach.call(speedBox.children, function(c, i) {
        var vals = [0.5, 1, 2];
        c.style.border = vals[i] === s ? '1px solid #3b82f6' : '1px solid #374151';
        c.style.color = vals[i] === s ? '#3b82f6' : '#9ca3af';
        c.style.background = vals[i] === s ? 'rgba(59,130,246,0.15)' : 'transparent';
      });
    });
    speedBox.appendChild(b);
  });

  var seekbar = document.getElementById('seekbar');
  var seeking = false;
  function seekTo(e) {
    var rect = seekbar.getBoundingClientRect();
    var pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    currentSample = Math.max(windowSamples, pct * totalSamples);
    updateUI(); draw();
  }
  seekbar.addEventListener('mousedown', function(e) { seeking = true; seekTo(e); });
  document.addEventListener('mousemove', function(e) { if (seeking) seekTo(e); });
  document.addEventListener('mouseup', function() { seeking = false; });

  draw(); updateUI();
})();
</script>
""")
