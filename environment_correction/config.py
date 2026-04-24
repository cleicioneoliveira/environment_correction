"""Configuration models for the environmental correction utility.

This module contains immutable dataclasses used to centralize all runtime
parameters. Keeping configuration in one place makes the pipeline easier to
inspect, test and reproduce.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

HumidityUnit = Literal["auto", "pct", "fraction"]
AggregationMethod = Literal["mean", "median"]
LagMode = Literal["independent", "shared"]


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for the environmental correction pipeline.

    Parameters
    ----------
    heat_path : Path
        Path to the heat stress report CSV. This file is treated as the source
        of truth for temperature and relative humidity.
    monitoramento_path : Path
        Path to the monitoring CSV to be corrected.
    output_monitoramento : Path
        Path where the corrected monitoring CSV will be written.
    output_audit : Path
        Path where all compost/device/lag candidate metrics will be written.
    output_pair_candidates : Path
        Path where candidate device pairs will be written.
    output_summary : Path
        Path where the JSON execution summary will be written.
    output_quality : Path
        Path where the quality summary CSV will be written.
    output_inconsistencies : Path
        Path where duplicated/inconsistent hourly environmental values found in
        the monitoring file will be written.
    output_coverage : Path
        Path where correction coverage by compost will be written.
    log_level : str
        Python logging level.
    lag_min : int
        Minimum lag, in hours, to test. Negative lags move heat timestamps
        backwards when compared with monitoring timestamps.
    lag_max : int
        Maximum lag, in hours, to test. Positive lags move heat timestamps
        forwards when compared with monitoring timestamps.
    min_overlap_hours : int
        Minimum number of overlapping hourly records required to evaluate a
        compost/device/lag candidate.
    lag_mode : {'independent', 'shared'}
        If ``independent``, each compost can use its own best lag. If
        ``shared``, both composts must use the same lag.
    humidity_unit : {'auto', 'pct', 'fraction'}
        Relative humidity unit in the heat file. ``auto`` detects values in
        [0, 1] and converts them to percentage.
    aggregation : {'mean', 'median'}
        Hourly aggregation method for heat temperature and humidity.
    min_score_margin : float
        Minimum desired difference between the best and second-best candidate.
        This does not stop execution by itself; it is reported as an uncertainty
        flag. Use ``fail_on_low_quality`` to turn warnings into errors.
    fail_on_low_quality : bool
        If true, stop execution when selected mappings fail quality checks.
    """

    heat_path: Path
    monitoramento_path: Path
    output_monitoramento: Path
    output_audit: Path
    output_pair_candidates: Path
    output_summary: Path
    output_quality: Path
    output_inconsistencies: Path
    output_coverage: Path
    log_level: str
    lag_min: int
    lag_max: int
    min_overlap_hours: int
    lag_mode: LagMode
    humidity_unit: HumidityUnit
    aggregation: AggregationMethod
    min_score_margin: float
    fail_on_low_quality: bool
