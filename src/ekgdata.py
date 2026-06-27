import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy.signal import find_peaks as scipy_find_peaks


class EKGdata:

    SIGNAL_COLUMNS = ["MLII", "V5", "V1", "V2"]
    SAMPLE_RATE = 360

    BRADYCARDIA_THRESHOLD = 60
    TACHYCARDIA_THRESHOLD = 100

    def __init__(self, ekg_dict, df):
        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        self.result_link = ekg_dict["result_link"]
        self.df = df
        self.signal_col = self._detect_signal_column()
        self.peaks = None
        self.heart_rate = None
        self._anomalies = None

    @property
    def duration_s(self):
        return len(self.df) / self.SAMPLE_RATE

    def _detect_signal_column(self):
        for col in self.SIGNAL_COLUMNS:
            if col in self.df.columns:
                return col
        return self.df.columns[0]

    def find_peaks(self, distance=200):
        signal = self.df[self.signal_col].values
        sig_min, sig_max = np.min(signal), np.max(signal)
        height = sig_min + 0.6 * (sig_max - sig_min)
        peaks, _ = scipy_find_peaks(signal, height=height, distance=distance)
        self.peaks = peaks.tolist()
        return self.peaks

    def estimate_hr(self, start_s=None, end_s=None):
        if self.peaks is None:
            self.find_peaks()

        times = self.df["Zeit in s"].iloc[self.peaks].values

        if start_s is not None and end_s is not None:
            mask = (times >= start_s) & (times <= end_s)
            times = times[mask]

        if len(times) < 2:
            if start_s is None:
                self.heart_rate = 0
            return 0

        intervals_s = np.diff(times)
        mean_interval_s = np.mean(intervals_s)
        hr = round(60.0 / mean_interval_s)

        if start_s is None:
            self.heart_rate = hr
        return hr

    def get_peaks_in_range(self, start_s, end_s):
        if self.peaks is None:
            self.find_peaks()
        times = self.df["Zeit in s"].iloc[self.peaks].values
        mask = (times >= start_s) & (times <= end_s)
        return np.array(self.peaks)[mask].tolist()

    @property
    def total_peaks_count(self):
        if self.peaks is None:
            self.find_peaks()
        return len(self.peaks)

    def calc_hrv(self):
        """Calculate HRV metrics: SDNN and RMSSD from R-R intervals."""
        if self.peaks is None:
            self.find_peaks()
        times = self.df["Zeit in s"].iloc[self.peaks].values
        if len(times) < 3:
            return {"sdnn": None, "rmssd": None}

        rr_intervals_ms = np.diff(times) * 1000
        sdnn = float(np.std(rr_intervals_ms, ddof=1))
        successive_diffs = np.diff(rr_intervals_ms)
        rmssd = float(np.sqrt(np.mean(successive_diffs ** 2)))
        return {"sdnn": round(sdnn, 1), "rmssd": round(rmssd, 1)}

    def get_hr_stats(self):
        """Min, Max, and Mean instantaneous HR from R-R intervals."""
        if self.peaks is None:
            self.find_peaks()
        times = self.df["Zeit in s"].iloc[self.peaks].values
        if len(times) < 2:
            return {"min": 0, "max": 0, "mean": 0}
        intervals = np.diff(times)
        hr_values = 60.0 / intervals
        hr_values = hr_values[(hr_values > 20) & (hr_values < 250)]
        if len(hr_values) == 0:
            return {"min": 0, "max": 0, "mean": 0}
        return {
            "min": int(np.min(hr_values)),
            "max": int(np.max(hr_values)),
            "mean": int(np.mean(hr_values)),
        }

    # ── Anomaly Detection ──

    def detect_anomalies(self):
        """Detect cardiac anomalies using robust statistics (median + MAD).

        Categories:
        - irregular: RR interval deviates > 3 MAD-scaled σ from median AND
                     at least 20% relative deviation (filters out noise)
        - dropout: RR interval > 1.8× the median (missed beat / pause)
        - tachycardia: instantaneous HR > 100 bpm (sustained, not just one-off)
        - bradycardia: instantaneous HR < 60 bpm
        """
        if self._anomalies is not None:
            return self._anomalies

        if self.peaks is None:
            self.find_peaks()

        times = self.df["Zeit in s"].iloc[self.peaks].values
        if len(times) < 3:
            self._anomalies = []
            return self._anomalies

        intervals = np.diff(times)
        median_rr = np.median(intervals)
        mad = np.median(np.abs(intervals - median_rr))
        mad_sigma = mad * 1.4826 if mad > 0 else np.std(intervals, ddof=1)
        hr_instant = 60.0 / intervals

        anomalies = []

        for i, (rr, hr) in enumerate(zip(intervals, hr_instant)):
            t_start = float(times[i])
            t_end = float(times[i + 1])
            deviation = abs(rr - median_rr)
            relative_dev = deviation / median_rr if median_rr > 0 else 0

            if rr > 1.8 * median_rr:
                anomalies.append({
                    "type": "dropout",
                    "time_s": t_start,
                    "time_end_s": t_end,
                    "rr_ms": round(rr * 1000, 1),
                    "hr": round(hr, 1),
                })
            elif mad_sigma > 0 and deviation > 3 * mad_sigma and relative_dev > 0.20:
                sigma_val = round(deviation / mad_sigma, 1)
                anomalies.append({
                    "type": "irregular",
                    "time_s": t_start,
                    "time_end_s": t_end,
                    "rr_ms": round(rr * 1000, 1),
                    "hr": round(hr, 1),
                    "deviation_sigma": sigma_val,
                })
            elif hr > self.TACHYCARDIA_THRESHOLD:
                anomalies.append({
                    "type": "tachycardia",
                    "time_s": t_start,
                    "time_end_s": t_end,
                    "hr": round(hr, 1),
                })
            elif hr < self.BRADYCARDIA_THRESHOLD:
                anomalies.append({
                    "type": "bradycardia",
                    "time_s": t_start,
                    "time_end_s": t_end,
                    "hr": round(hr, 1),
                })

        self._anomalies = anomalies
        return anomalies

    def get_anomaly_summary(self):
        """Grouped counts and severity assessment."""
        anomalies = self.detect_anomalies()
        counts = {"irregular": 0, "dropout": 0, "tachycardia": 0, "bradycardia": 0}
        for a in anomalies:
            counts[a["type"]] += 1

        total = sum(counts.values())
        if total == 0:
            severity = "normal"
        elif counts["dropout"] > 0 or total > 10:
            severity = "warning"
        else:
            severity = "attention"

        return {"counts": counts, "total": total, "severity": severity}

    def get_anomalies_in_range(self, start_s, end_s):
        anomalies = self.detect_anomalies()
        return [a for a in anomalies if a["time_s"] >= start_s and a["time_s"] <= end_s]

    # ── Plots ──

    def plot_detail(self, start_s, end_s, show_anomalies=True):
        """Full-resolution plot for a selected time window with peak and anomaly markers."""
        df = self.df
        mask = (df["Zeit in s"] >= start_s) & (df["Zeit in s"] <= end_s)
        plot_df = df[mask]

        peaks_in_range = self.get_peaks_in_range(start_s, end_s)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=plot_df["Zeit in s"],
            y=plot_df[self.signal_col],
            mode="lines",
            name="EKG-Signal",
            line=dict(width=1.2, color="#1f77b4"),
        ))

        if peaks_in_range:
            peak_times = df["Zeit in s"].iloc[peaks_in_range].values
            peak_vals = df[self.signal_col].iloc[peaks_in_range].values
            fig.add_trace(go.Scatter(
                x=peak_times,
                y=peak_vals,
                mode="markers",
                name="R-Peaks",
                marker=dict(size=7, color="#2ecc71", symbol="triangle-down"),
            ))

        if show_anomalies:
            anomalies = self.get_anomalies_in_range(start_s, end_s)
            for a in anomalies:
                color = {
                    "dropout": "rgba(231, 76, 60, 0.25)",
                    "irregular": "rgba(243, 156, 18, 0.2)",
                    "tachycardia": "rgba(255, 87, 34, 0.15)",
                    "bradycardia": "rgba(52, 152, 219, 0.15)",
                }.get(a["type"], "rgba(231, 76, 60, 0.15)")

                fig.add_vrect(
                    x0=a["time_s"], x1=a["time_end_s"],
                    fillcolor=color,
                    layer="below",
                    line_width=0,
                    annotation_text=a["type"][:5],
                    annotation_position="top left",
                    annotation_font_size=9,
                    annotation_font_color="#e74c3c" if a["type"] in ("dropout", "irregular") else "#888",
                )

        fig.update_layout(
            xaxis_title="Zeit [s]",
            yaxis_title="Spannung [mV]",
            height=400,
            margin=dict(l=50, r=20, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            hovermode="x unified",
            xaxis=dict(
                rangeslider=dict(visible=True, thickness=0.08),
            ),
            dragmode="pan",
        )
        fig.update_xaxes(fixedrange=False)
        fig.update_yaxes(fixedrange=True)
        return fig

    def plot_overview(self, max_points=5000):
        """Downsampled overview of the entire signal for navigation."""
        df = self.df
        step = max(1, len(df) // max_points)
        plot_df = df.iloc[::step]

        fig = go.Figure()
        fig.add_trace(go.Scattergl(
            x=plot_df["Zeit in s"],
            y=plot_df[self.signal_col],
            mode="lines",
            name="EKG-Signal",
            line=dict(width=0.8, color="#7f8c8d"),
        ))

        fig.update_layout(
            height=120,
            margin=dict(l=50, r=20, t=10, b=30),
            xaxis_title="Zeit [s]",
            yaxis=dict(showticklabels=False),
            showlegend=False,
        )
        return fig

    def plot_monitor_frame(self, center_s, window_s=6.0):
        """Single frame for the live monitor view — dark background, green trace."""
        df = self.df
        start_s = max(0, center_s - window_s)
        end_s = center_s
        mask = (df["Zeit in s"] >= start_s) & (df["Zeit in s"] <= end_s)
        plot_df = df[mask]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_df["Zeit in s"],
            y=plot_df[self.signal_col],
            mode="lines",
            line=dict(width=2, color="#00ff41"),
            showlegend=False,
        ))

        fig.update_layout(
            height=300,
            margin=dict(l=50, r=20, t=10, b=30),
            paper_bgcolor="#1a1a2e",
            plot_bgcolor="#1a1a2e",
            xaxis=dict(
                showgrid=True,
                gridcolor="#2d2d44",
                gridwidth=0.5,
                color="#888",
                title="Zeit [s]",
                range=[start_s, start_s + window_s],
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#2d2d44",
                gridwidth=0.5,
                color="#888",
                showticklabels=False,
            ),
        )
        return fig

    def plot_hr_trend(self):
        """Heart rate over time with tachycardia/bradycardia reference zones."""
        if self.peaks is None:
            self.find_peaks()

        times = self.df["Zeit in s"].iloc[self.peaks].values
        if len(times) < 3:
            return None

        intervals = np.diff(times)
        hr_values = 60.0 / intervals
        hr_times_min = times[1:] / 60.0

        kernel_size = min(5, len(hr_values))
        if kernel_size > 1:
            kernel = np.ones(kernel_size) / kernel_size
            hr_smooth = np.convolve(hr_values, kernel, mode="same")
        else:
            hr_smooth = hr_values

        fig = go.Figure()

        y_min = max(30, np.min(hr_smooth) - 10)
        y_max = min(220, np.max(hr_smooth) + 10)

        fig.add_hrect(
            y0=self.BRADYCARDIA_THRESHOLD, y1=self.TACHYCARDIA_THRESHOLD,
            fillcolor="rgba(46, 204, 113, 0.08)",
            layer="below", line_width=0,
        )
        fig.add_hline(
            y=self.TACHYCARDIA_THRESHOLD,
            line_dash="dash", line_color="rgba(231, 76, 60, 0.5)", line_width=1,
            annotation_text="Tachykardie (>100)",
            annotation_position="top right",
            annotation_font_size=10,
            annotation_font_color="#e74c3c",
        )
        fig.add_hline(
            y=self.BRADYCARDIA_THRESHOLD,
            line_dash="dash", line_color="rgba(52, 152, 219, 0.5)", line_width=1,
            annotation_text="Bradykardie (<60)",
            annotation_position="bottom right",
            annotation_font_size=10,
            annotation_font_color="#3498db",
        )

        fig.add_trace(go.Scatter(
            x=hr_times_min,
            y=hr_smooth,
            mode="lines",
            name="Herzfrequenz",
            line=dict(width=1.5, color="#e74c3c"),
        ))

        fig.update_layout(
            xaxis_title="Zeit [min]",
            yaxis_title="HR [bpm]",
            yaxis_range=[y_min, y_max],
            height=250,
            margin=dict(l=50, r=20, t=10, b=40),
            showlegend=False,
        )
        return fig
