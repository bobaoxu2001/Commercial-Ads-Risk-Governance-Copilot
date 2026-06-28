from __future__ import annotations

import pandas as pd


def daily_anomalies(scores: pd.DataFrame) -> list[dict[str, object]]:
    if scores.empty:
        return []
    frame = scores.copy()
    frame["date"] = pd.to_datetime(frame["case_date"], errors="coerce").dt.date
    daily = frame.dropna(subset=["date"]).groupby("date").size().rename("cases").reset_index()
    if daily.empty:
        return []
    mean = daily["cases"].mean()
    std = daily["cases"].std() or 0
    daily["z_score"] = ((daily["cases"] - mean) / std).fillna(0).round(2) if std else 0.0
    daily["is_anomaly"] = daily["z_score"].abs() >= 2
    daily["date"] = daily["date"].astype(str)
    return daily.tail(30).to_dict("records")
