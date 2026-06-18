import pandas as pd
import plotly.express as px
import numpy as np


class EKGdata:

    def __init__(self, ekg_dict, df):
        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        self.result_link = ekg_dict["result_link"]
        self.df = df
        self.peaks = None
        self.heart_rate = None

    def find_peaks(self, threshold=0.5, min_distance=200):
        signal = self.df['MLII'].values
        peaks = []
        last_peak = -min_distance
        for i in range(1, len(signal) - 1):
            if (signal[i] > threshold and
                signal[i] > signal[i - 1] and
                signal[i] > signal[i + 1] and
                (i - last_peak) >= min_distance):
                peaks.append(i)
                last_peak = i
        self.peaks = peaks
        return peaks

    def estimate_hr(self):
        if self.peaks is None:
            self.find_peaks()
        if len(self.peaks) < 2:
            self.heart_rate = 0
            return 0
        times = self.df['Zeit in ms'].iloc[self.peaks].values
        intervals_ms = np.diff(times)
        mean_interval_s = np.mean(intervals_ms) / 1000.0
        self.heart_rate = round(60.0 / mean_interval_s)
        return self.heart_rate

    def plot_time_series(self):
        if self.peaks is None:
            self.find_peaks()
        fig = px.line(self.df, x="Zeit in ms", y="MLII", title="EKG-Signal")
        if self.peaks:
            peak_df = self.df.iloc[self.peaks]
            fig.add_scatter(
                x=peak_df["Zeit in ms"], y=peak_df["MLII"],
                mode="markers", marker=dict(color="red", size=8), name="Peaks"
            )
        fig.update_layout(xaxis_title="Zeit [ms]", yaxis_title="Spannung [mV]")
        return fig
