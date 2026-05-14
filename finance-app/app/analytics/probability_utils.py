from __future__ import annotations

import numpy as np
import pandas as pd


def empirical_probability_greater_than(values: pd.Series, threshold: float) -> float:
    clean = values.dropna().astype(float)
    if clean.empty:
        return 0.0
    return float((clean > threshold).mean())


def zscore_anomalies(expenses_frame: pd.DataFrame, z_threshold: float, limit: int = 20) -> list[dict]:
    if expenses_frame.empty:
        return []

    std = float(expenses_frame["amount"].std(ddof=0))
    if std == 0:
        return []

    mean = float(expenses_frame["amount"].mean())
    work = expenses_frame.copy()
    work["z_score"] = (work["amount"] - mean) / std
    filtered = work[work["z_score"].abs() >= z_threshold].sort_values(
        "z_score", key=lambda s: s.abs(), ascending=False
    )

    return [
        {
            "transaction_id": int(row["transaction_id"]),
            "transaction_date": row["transaction_date"].strftime("%Y-%m-%d"),
            "amount": float(row["amount"]),
            "z_score": float(row["z_score"]),
        }
        for _, row in filtered.head(limit).iterrows()
    ]


def normal_confidence_interval(values: pd.Series, confidence_level: float) -> dict:
    clean = values.dropna().astype(float)
    if clean.empty:
        return {
            "confidence_level": confidence_level,
            "lower_bound": None,
            "upper_bound": None,
            "mean": None,
        }

    mean = float(clean.mean())
    std = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
    n = len(clean)

    z_map = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_map.get(round(confidence_level, 2), 1.96)
    margin = z * (std / np.sqrt(n)) if n > 0 else 0.0

    return {
        "confidence_level": confidence_level,
        "lower_bound": float(mean - margin),
        "upper_bound": float(mean + margin),
        "mean": mean,
    }
