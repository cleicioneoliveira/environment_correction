"""Numerical metrics used for mapping, validation and audit reports."""

from __future__ import annotations

import math

import pandas as pd


def safe_corr(a: pd.Series, b: pd.Series, min_n: int = 3) -> float:
    """Calculate Pearson correlation with guards against invalid inputs.

    Parameters
    ----------
    a, b : pandas.Series
        Series to correlate.
    min_n : int, optional
        Minimum number of complete paired observations.

    Returns
    -------
    float
        Pearson correlation, or NaN when the correlation is not reliable or not
        mathematically defined.
    """

    df = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(df) < min_n:
        return float("nan")
    if df["a"].nunique(dropna=True) < 2 or df["b"].nunique(dropna=True) < 2:
        return float("nan")
    return float(df["a"].corr(df["b"]))


def mean_absolute_error(a: pd.Series, b: pd.Series) -> float:
    """Calculate mean absolute error after pairwise NaN removal."""

    df = pd.DataFrame({"a": a, "b": b}).dropna()
    if df.empty:
        return float("nan")
    return float((df["a"] - df["b"]).abs().mean())


def round_match_rate(a: pd.Series, b: pd.Series) -> float:
    """Calculate match rate after integer rounding.

    This is useful when the original monitoring file appears to have lost
    decimals and should be compared at integer precision.
    """

    df = pd.DataFrame({"a": a, "b": b}).dropna()
    if df.empty:
        return float("nan")
    return float((df["a"].round().astype(int) == df["b"].round().astype(int)).mean())


def mapping_score(corr_temp: float, corr_hum: float, mae_temp: float, mae_hum: float) -> float:
    """Calculate the mapping score used to rank compost/device/lag candidates.

    The score rewards high correlation and penalizes large absolute differences.
    Invalid correlations or errors return NaN so they can be excluded from the
    candidate ranking.
    """

    values = [corr_temp, corr_hum, mae_temp, mae_hum]
    if any(math.isnan(v) for v in values):
        return float("nan")
    return float((corr_temp + corr_hum) / 2 - 0.01 * (mae_temp + mae_hum))
