import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy.signal import find_peaks as scipy_find_peaks


class EKGdata:

    SIGNAL_COLUMNS = ["MLII", "V5", "V1", "V2"]
    SAMPLE_RATE = 360

    def __init__(self, ekg_dict, df):
        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        self.result_link = ekg_dict["result_link"]
        self.df = df
        self.signal_col = self._detect_signal_column()
        self.peaks = None
        self.heart_rate = None

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

    def plot_detail(self, start_s, end_s):
        """Full-resolution plot for a selected time window with peak markers."""
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
                marker=dict(size=7, color="#e74c3c", symbol="triangle-down"),
            ))

        fig.update_layout(
            xaxis_title="Zeit [s]",
            yaxis_title="Spannung [mV]",
            height=350,
            margin=dict(l=50, r=20, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            hovermode="x unified",
        )
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

    def plot_hr_trend(self, window_s=10.0):
        """Heart rate over time using a sliding window."""
        if self.peaks is None:
            self.find_peaks()

        times = self.df["Zeit in s"].iloc[self.peaks].values
        if len(times) < 3:
            return None

        intervals = np.diff(times)
        hr_values = 60.0 / intervals
        hr_times = times[1:]

        kernel_size = min(5, len(hr_values))
        if kernel_size > 1:
            kernel = np.ones(kernel_size) / kernel_size
            hr_smooth = np.convolve(hr_values, kernel, mode="same")
        else:
            hr_smooth = hr_values

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hr_times,
            y=hr_smooth,
            mode="lines",
            name="Herzfrequenz",
            line=dict(width=1.5, color="#e74c3c"),
        ))

        fig.update_layout(
            xaxis_title="Zeit [s]",
            yaxis_title="HR [bpm]",
            height=200,
            margin=dict(l=50, r=20, t=10, b=40),
            showlegend=False,
        )
        return fig
