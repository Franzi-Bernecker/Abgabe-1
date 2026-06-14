import json
import pandas as pd
import plotly.express as px
import numpy as np


class EKGdata:
    # Pfad zur Personen-DB (da EKG-Tests dort verlinkt sind)
    DB_PATH = "data/person_db.json"

    def __init__(self, ekg_dict):
        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        self.result_link = ekg_dict["result_link"]
        # EKG-Datei einlesen (Tab-getrennt, 2 Spalten)
        self.df = pd.read_csv(
            self.result_link, sep='\t', header=None,
            names=['Messwerte in mV', 'Zeit in ms']
        )
        self.peaks = None
        self.heart_rate = None

    @staticmethod
    def load_by_id(ekg_id):
        with open(EKGdata.DB_PATH, "r", encoding="utf-8") as file:
            person_data = json.load(file)
        for person in person_data:
            for test in person.get("ekg_tests", []):
                if test["id"] == ekg_id:
                    return EKGdata(test)
        return None

    def find_peaks(self, threshold=340, min_distance=200):
        # Einfache Peak-Detection: über Schwellenwert + lokales Maximum
        signal = self.df['Messwerte in mV'].values
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
        # HR = 60 / mittlerer Abstand zwischen Peaks in Sekunden
        times = self.df['Zeit in ms'].iloc[self.peaks].values
        intervals_ms = np.diff(times)
        mean_interval_s = np.mean(intervals_ms) / 1000.0
        self.heart_rate = round(60.0 / mean_interval_s)
        return self.heart_rate

    def plot_time_series(self):
        if self.peaks is None:
            self.find_peaks()
        fig = px.line(self.df, x="Zeit in ms", y="Messwerte in mV", title="EKG-Signal")
        # Peaks als rote Punkte einzeichnen
        if self.peaks:
            peak_df = self.df.iloc[self.peaks]
            fig.add_scatter(
                x=peak_df["Zeit in ms"], y=peak_df["Messwerte in mV"],
                mode="markers", marker=dict(color="red", size=8), name="Peaks"
            )
        fig.update_layout(xaxis_title="Zeit [ms]", yaxis_title="Spannung [mV]")
        return fig


if __name__ == "__main__":
    ekg = EKGdata.load_by_id(1)
    if ekg:
        ekg.find_peaks()
        print(f"Peaks: {len(ekg.peaks)}, HR: {ekg.estimate_hr()} bpm")
