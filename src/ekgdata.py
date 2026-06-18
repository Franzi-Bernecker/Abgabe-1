import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.signal import find_peaks as scipy_find_peaks


class EKGdata:

    SIGNAL_COLUMNS = ["MLII", "V5", "V1", "V2"]

    def __init__(self, ekg_dict, df):
        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        self.result_link = ekg_dict["result_link"]
        self.df = df
        self.signal_col = self._detect_signal_column()
        self.peaks = None
        self.heart_rate = None

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

    def estimate_hr(self):
        if self.peaks is None:
            self.find_peaks()
        if len(self.peaks) < 2:
            self.heart_rate = 0
            return 0
        times = self.df["Zeit in s"].iloc[self.peaks].values
        intervals_s = np.diff(times)
        mean_interval_s = np.mean(intervals_s)
        self.heart_rate = round(60.0 / mean_interval_s)
        return self.heart_rate

    def plot_time_series(self, max_points=10000):
        if self.peaks is None:
            self.find_peaks()

        df = self.df
        step = max(1, len(df) // max_points)
        plot_df = df.iloc[::step] if step > 1 else df

        fig = go.Figure()

        fig.add_trace(go.Scattergl(
            x=plot_df["Zeit in s"],
            y=plot_df[self.signal_col],
            mode="lines",
            name="EKG-Signal",
            line=dict(width=1),
        ))

        fig.update_layout(
            title="EKG-Signal",
            xaxis_title="Zeit [s]",
            yaxis_title="Spannung [mV]",
            xaxis=dict(rangeslider=dict(visible=True)),
        )
        return fig
