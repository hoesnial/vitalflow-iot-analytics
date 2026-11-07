"""Shared dashboard calculations and missing-aware chart inputs."""

from dataclasses import dataclass

import pandas as pd

from vitalflow.source import MEASURES

from .evidence import Snapshot


@dataclass(frozen=True)
class Channel:
    label: str
    unit: str
    description: str


CHANNELS = {
    "hr": Channel("HR", "denyut/menit", "Denyut jantung dari monitor ECG"),
    "pulse": Channel("PULSE", "denyut/menit", "Laju nadi dari monitor PPG"),
    "resp": Channel("RESP", "napas/menit", "Laju pernapasan dari monitor"),
    "spo2": Channel("SpO₂", "%", "Saturasi oksigen dari monitor"),
}


def filter_recording(frame: pd.DataFrame, start: float, end: float) -> pd.DataFrame:
    if start > end:
        raise ValueError("Time range must be ordered")
    return frame.loc[frame["time_s"].between(start, end)].copy()


def observed_stats(frame: pd.DataFrame, channels: tuple[str, ...]) -> list[dict]:
    result = []
    for key in channels:
        values = frame[key].dropna()
        result.append(
            {
                "Kanal": CHANNELS[key].label,
                "Unit": CHANNELS[key].unit,
                "Total": len(frame),
                "Valid": len(values),
                "Hilang": len(frame) - len(values),
                "Minimum": values.min() if len(values) else None,
                "Maksimum": values.max() if len(values) else None,
                "Rata-rata": values.mean() if len(values) else None,
            }
        )
    return result


def series_with_gaps(
    time: pd.Series, values: pd.Series, expected_step: float
) -> tuple[list[float], list[float | None], list[float]]:
    """Preserve explicit nulls and break the line across absent time slots."""
    x: list[float] = []
    y: list[float | None] = []
    missing: list[float] = []
    for at, value in zip(time, values, strict=True):
        tick = float(at)
        if x and tick - x[-1] > expected_step + 1e-6:
            x.append(x[-1] + expected_step)
            y.append(None)
        x.append(tick)
        y.append(None if pd.isna(value) else float(value))
        if y[-1] is None:
            missing.append(tick)
    return x, y, missing


def clean_missing_by_recording(snapshot: Snapshot) -> pd.DataFrame:
    result = snapshot.recordings[["recording_id", "rows"]].copy()
    for key in MEASURES:
        result[key] = result["rows"] - snapshot.recordings[f"{key}_valid"]
    result["missing"] = result[list(MEASURES)].sum(axis=1)
    result["complete_pct"] = 100 * (1 - result["missing"] / (len(MEASURES) * result["rows"]))
    return result


def source_missing_by_recording(snapshot: Snapshot, channel: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "recording_id": item["recording_id"],
                "missing": sum(item["lexical_types"][channel].get(k, 0) for k in ("blank", "nan")),
                "rows": item["rows"],
            }
            for item in snapshot.profiles
        ]
    )


def complete_minute_pair(snapshot: Snapshot, recording: str) -> tuple[pd.Series, pd.Series] | None:
    """Use full expected sampling windows and verify that every channel is complete."""
    width = snapshot.run["analytics_window_seconds"]
    hz = snapshot.metadata[recording]["numerics_sampling_hz"]
    expected = width * hz
    if expected != int(expected):
        return None
    windows = snapshot.windows[snapshot.windows["recording_id"] == recording]
    complete = windows.loc[
        (windows["rows"] == int(expected))
        & ((windows["first_time_s"] - windows["window_start_s"]).abs() < 1e-6)
        & ((windows["last_time_s"] - windows["window_start_s"] - width + 1 / hz).abs() < 1e-6)
        & windows[[f"{key}_valid" for key in MEASURES]].eq(windows["rows"], axis=0).all(axis=1)
    ].sort_values("window_start_s")
    if len(complete) < 2:
        return None
    return complete.iloc[0], complete.iloc[-1]
