"""Quality, coverage and summary reports for the environmental correction."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .metrics import mean_absolute_error, round_match_rate, safe_corr
from .thi import thi_cattle


def build_quality_summary(
    heat_hourly: pd.DataFrame,
    env_hourly: pd.DataFrame,
    device_map: dict[int, dict[str, int]],
) -> pd.DataFrame:
    """Build quality metrics for the selected device/lag mapping.

    Metrics compare the original monitoring environmental columns with the heat
    source selected for each compost. They are audit metrics, not the correction
    itself.
    """

    rows: list[dict[str, Any]] = []

    for compost in (1, 2):
        device = device_map[compost]["device"]
        lag_h = device_map[compost]["lag_hours"]

        src = heat_hourly[heat_hourly["dispositivo"] == device].copy()
        src["data_hora"] = src["data_hora_bruta"] + pd.Timedelta(hours=lag_h)
        tmp = env_hourly.reset_index().merge(src, on="data_hora", how="inner")
        calc_thi = thi_cattle(tmp["temperature"], tmp["humidity"])

        rows.extend(
            [
                _quality_row(
                    compost,
                    "temperatura",
                    f"temperatura_compost_{compost}",
                    device,
                    lag_h,
                    tmp[f"temperatura_compost_{compost}"],
                    tmp["temperature"],
                ),
                _quality_row(
                    compost,
                    "umidade",
                    f"humidade_compost_{compost}",
                    device,
                    lag_h,
                    tmp[f"humidade_compost_{compost}"],
                    tmp["humidity"],
                ),
                _quality_row(
                    compost,
                    "thi_recalculado",
                    f"thi_compost{compost}",
                    device,
                    lag_h,
                    tmp[f"thi_compost{compost}"],
                    calc_thi,
                ),
            ]
        )

    return pd.DataFrame(rows)


def _quality_row(
    compost: int,
    metric: str,
    monitor_col: str,
    device: int,
    lag_h: int,
    original: pd.Series,
    source: pd.Series,
) -> dict[str, Any]:
    """Create a single quality report row."""

    return {
        "compost": compost,
        "metric": metric,
        "monitor_col": monitor_col,
        "source_device": int(device),
        "lag_hours": int(lag_h),
        "corr": safe_corr(original, source),
        "mae": mean_absolute_error(original, source),
        "round_match_rate": round_match_rate(original, source),
        "n": int(pd.DataFrame({"a": original, "b": source}).dropna().shape[0]),
    }


def build_coverage_summary(mon: pd.DataFrame, corrected_env: pd.DataFrame) -> pd.DataFrame:
    """Calculate correction coverage by compost."""

    rows: list[dict[str, Any]] = []
    merged = mon[["data_hora"]].merge(corrected_env, on="data_hora", how="left")
    total_rows = len(mon)

    for compost in (1, 2):
        temp_col = f"temperatura_compost_{compost}_corrigida"
        hum_col = f"humidade_compost_{compost}_corrigida"
        thi_col = f"thi_compost{compost}_corrigido"
        corrected_rows = int(merged[[temp_col, hum_col, thi_col]].notna().all(axis=1).sum())
        rows.append(
            {
                "compost": compost,
                "total_monitoramento_rows": int(total_rows),
                "corrected_rows": corrected_rows,
                "uncorrected_rows": int(total_rows - corrected_rows),
                "coverage_pct": float(corrected_rows / total_rows * 100) if total_rows else 0.0,
            }
        )

    return pd.DataFrame(rows)


def build_summary(
    heat: pd.DataFrame,
    mon: pd.DataFrame,
    mon_corr: pd.DataFrame,
    device_map: dict[int, dict[str, int]],
    quality_df: pd.DataFrame,
    coverage_df: pd.DataFrame,
    uncertainty: dict[str, Any],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Build the JSON execution summary."""

    return {
        "parameters": parameters,
        "rows_heat": int(len(heat)),
        "rows_monitoramento_original": int(len(mon)),
        "rows_monitoramento_corrigido": int(len(mon_corr)),
        "date_range_heat": [str(heat["timestamp"].min()), str(heat["timestamp"].max())],
        "date_range_monitoramento": [str(mon["data_hora"].min()), str(mon["data_hora"].max())],
        "device_map": device_map,
        "coverage": coverage_df.to_dict(orient="records"),
        "uncertainty": uncertainty,
        "quality_summary": quality_df.to_dict(orient="records"),
    }
