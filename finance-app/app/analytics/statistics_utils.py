from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd


def safe_float(value: float | int | np.floating | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, np.floating)) and (math.isnan(value) or math.isinf(value)):
        return None
    return float(value)


def compute_descriptive_statistics(values: pd.Series, percentile_points: list[int] | None = None) -> dict:
    clean = values.dropna().astype(float)
    n = int(clean.size)
    if percentile_points is None:
        percentile_points = [5, 10, 25, 50, 75, 90, 95]

    if n == 0:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "mode": [],
            "variance": None,
            "standard_deviation": None,
            "quartile_1": None,
            "quartile_2": None,
            "quartile_3": None,
            "percentiles": [{"percentile": p, "value": 0.0} for p in percentile_points],
            "interquartile_range": None,
            "coefficient_of_variation": None,
            "min_value": None,
            "max_value": None,
            "range_value": None,
        }

    counts = Counter(clean.tolist())
    highest_freq = max(counts.values())
    modes = sorted([float(k) for k, v in counts.items() if v == highest_freq])

    q1 = float(clean.quantile(0.25))
    q2 = float(clean.quantile(0.50))
    q3 = float(clean.quantile(0.75))
    mean = float(clean.mean())
    std = float(clean.std(ddof=0)) if n > 0 else None

    percentiles = [
        {"percentile": p, "value": float(clean.quantile(p / 100.0))}
        for p in percentile_points
    ]

    return {
        "count": n,
        "mean": safe_float(mean),
        "median": safe_float(q2),
        "mode": modes,
        "variance": safe_float(float(clean.var(ddof=0))),
        "standard_deviation": safe_float(std),
        "quartile_1": safe_float(q1),
        "quartile_2": safe_float(q2),
        "quartile_3": safe_float(q3),
        "percentiles": percentiles,
        "interquartile_range": safe_float(q3 - q1),
        "coefficient_of_variation": safe_float((std / mean) if mean not in (0.0, -0.0) else None),
        "min_value": safe_float(float(clean.min())),
        "max_value": safe_float(float(clean.max())),
        "range_value": safe_float(float(clean.max() - clean.min())),
    }


def compute_distribution_summary(values: pd.Series) -> dict:
    clean = values.dropna().astype(float)
    n = int(clean.size)
    if n == 0:
        return {
            "count": 0,
            "mean": None,
            "standard_deviation": None,
            "skewness": None,
            "kurtosis": None,
            "jarque_bera_statistic": None,
            "normality_p_value": None,
            "is_approximately_normal": False,
        }

    mean = float(clean.mean())
    std = float(clean.std(ddof=0)) if n > 0 else 0.0
    skew = float(clean.skew()) if n > 2 else 0.0
    kurt = float(clean.kurt()) if n > 3 else 0.0

    # Jarque-Bera approximation using chi-square(df=2) tail p-value = exp(-x/2)
    jb = (n / 6.0) * ((skew**2) + ((kurt**2) / 4.0))
    p_value = float(math.exp(-jb / 2.0))

    return {
        "count": n,
        "mean": safe_float(mean),
        "standard_deviation": safe_float(std),
        "skewness": safe_float(skew),
        "kurtosis": safe_float(kurt),
        "jarque_bera_statistic": safe_float(jb),
        "normality_p_value": safe_float(p_value),
        "is_approximately_normal": bool(p_value >= 0.05),
    }


def gaussian_kde_points(values: pd.Series, points: int = 100) -> list[dict]:
    clean = values.dropna().astype(float)
    n = int(clean.size)
    if n < 2:
        return []

    values_np = clean.to_numpy()
    x_min = float(values_np.min())
    x_max = float(values_np.max())
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    x_grid = np.linspace(x_min, x_max, points)
    std = float(values_np.std(ddof=1))
    bw = 1.06 * std * (n ** (-1 / 5)) if std > 0 else 1.0
    if bw <= 0:
        bw = 1.0

    coef = 1.0 / (n * bw * math.sqrt(2 * math.pi))
    densities = []
    for x in x_grid:
        z = (x - values_np) / bw
        density = coef * float(np.exp(-0.5 * (z ** 2)).sum())
        densities.append({"x": float(x), "y": density})
    return densities


def histogram_bins(values: pd.Series, bins: int = 12) -> list[dict]:
    clean = values.dropna().astype(float)
    if clean.empty:
        return []

    counts, edges = np.histogram(clean.to_numpy(), bins=bins)
    output = []
    for i, count in enumerate(counts):
        output.append(
            {
                "left": float(edges[i]),
                "right": float(edges[i + 1]),
                "count": int(count),
            }
        )
    return output


def boxplot_stats(values: pd.Series) -> dict | None:
    clean = values.dropna().astype(float)
    if clean.empty:
        return None
    return {
        "min_value": float(clean.min()),
        "q1": float(clean.quantile(0.25)),
        "median": float(clean.quantile(0.5)),
        "q3": float(clean.quantile(0.75)),
        "max_value": float(clean.max()),
    }
