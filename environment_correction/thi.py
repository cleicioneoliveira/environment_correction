"""Thermal comfort equations used by the environmental correction utility."""

from __future__ import annotations

import pandas as pd


def thi_cattle(temp_c: pd.Series, rh_pct: pd.Series) -> pd.Series:
    """Calculate the Temperature-Humidity Index for dairy cattle.

    The function assumes temperature in degrees Celsius and relative humidity in
    percentage from 0 to 100.

    Formula
    -------
    THI = (1.8 * T + 32) - (0.55 - 0.0055 * RH) * (1.8 * T - 26)

    Parameters
    ----------
    temp_c : pandas.Series
        Air temperature in degrees Celsius.
    rh_pct : pandas.Series
        Relative humidity in percentage.

    Returns
    -------
    pandas.Series
        Calculated THI values.
    """

    return (1.8 * temp_c + 32) - (0.55 - 0.0055 * rh_pct) * (1.8 * temp_c - 26)
