"""Device and lag inference for environmental correction."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from .config import LagMode
from .metrics import mapping_score, mean_absolute_error, safe_corr


def infer_mapping(
    heat: pd.DataFrame,
    heat_wide: pd.DataFrame,
    env_hourly: pd.DataFrame,
    lag_min: int,
    lag_max: int,
    min_overlap_hours: int,
    lag_mode: LagMode,
    min_score_margin: float,
    fail_on_low_quality: bool,
    logger: logging.Logger,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, dict[str, int]], dict[str, Any]]:
    """Infer the best heat device and lag for each compost environment.

    The inference compares each compost environmental series from the monitoring
    file against each device from the heat file. For each lag in the configured
    interval, heat timestamps are shifted by ``lag_hours`` before being joined to
    monitoring timestamps.

    A positive lag means the heat timestamp is moved forward in time before the
    comparison. A negative lag moves it backward. The selected lag should be
    interpreted as an operational alignment correction, not necessarily as a
    physical sensor delay.

    Parameters
    ----------
    heat : pandas.DataFrame
        Normalized heat input data.
    heat_wide : pandas.DataFrame
        Wide hourly heat table indexed by raw hourly timestamp.
    env_hourly : pandas.DataFrame
        Monitoring environmental table indexed by ``data_hora``.
    lag_min, lag_max : int
        Inclusive lag range, in hours.
    min_overlap_hours : int
        Minimum number of overlapping hourly rows required to score a candidate.
    lag_mode : {'independent', 'shared'}
        Lag strategy. ``shared`` forces both composts to use the same lag.
    min_score_margin : float
        Desired difference between best and second-best score for quality flagging.
    fail_on_low_quality : bool
        Whether to raise an error when quality checks fail.
    logger : logging.Logger
        Application logger.

    Returns
    -------
    tuple
        ``(audit_map, best_pairs_df, device_map, uncertainty)``.
    """

    if lag_min > lag_max:
        raise ValueError("lag_min não pode ser maior que lag_max.")

    logger.info(
        "Inferindo mapeamento dispositivo -> compost com lag entre %sh e %sh; modo=%s; overlap mínimo=%s h",
        lag_min,
        lag_max,
        lag_mode,
        min_overlap_hours,
    )

    devices = sorted(pd.to_numeric(heat["dispositivo"], errors="coerce").dropna().astype(int).unique().tolist())
    if len(devices) < 2:
        raise RuntimeError("São necessários pelo menos dois dispositivos válidos no heat para mapear compost_1 e compost_2.")

    audit_map = _build_candidate_audit(devices, heat_wide, env_hourly, lag_min, lag_max, min_overlap_hours)
    if audit_map.empty:
        raise RuntimeError(
            "Não foi possível gerar candidatos válidos de mapeamento. "
            "Verifique intervalo de datas, lag e min_overlap_hours."
        )

    audit_map = audit_map.sort_values(["compost", "score"], ascending=[True, False])

    if lag_mode == "shared":
        best_pairs_df = _build_shared_lag_pairs(devices, audit_map)
    else:
        best_pairs_df = _build_independent_lag_pairs(devices, audit_map)

    if best_pairs_df.empty:
        raise RuntimeError("Não foi possível encontrar par válido de dispositivos.")

    best_pairs_df = best_pairs_df.sort_values("pair_score", ascending=False)
    best_pair = best_pairs_df.iloc[0].to_dict()

    device_map = {
        1: {
            "device": int(best_pair["device_compost_1"]),
            "lag_hours": int(best_pair["lag_compost_1"]),
        },
        2: {
            "device": int(best_pair["device_compost_2"]),
            "lag_hours": int(best_pair["lag_compost_2"]),
        },
    }

    uncertainty = _build_uncertainty_report(audit_map, device_map, min_score_margin)
    low_quality = [row for row in uncertainty["compost_quality"] if row["low_score_margin"]]
    if low_quality:
        logger.warning(
            "Mapeamento com baixa margem de score detectado: %s",
            low_quality,
        )
        if fail_on_low_quality:
            raise RuntimeError(
                "Mapeamento considerado incerto por baixa margem de score. "
                "Revise device_lag_audit.csv ou reduza --min-score-margin conscientemente."
            )

    logger.info(
        "Mapeamento escolhido: compost_1 -> dispositivo %s (lag=%sh), compost_2 -> dispositivo %s (lag=%sh)",
        device_map[1]["device"],
        device_map[1]["lag_hours"],
        device_map[2]["device"],
        device_map[2]["lag_hours"],
    )

    return audit_map, best_pairs_df, device_map, uncertainty


def _build_candidate_audit(
    devices: list[int],
    heat_wide: pd.DataFrame,
    env_hourly: pd.DataFrame,
    lag_min: int,
    lag_max: int,
    min_overlap_hours: int,
) -> pd.DataFrame:
    """Build row-level audit table for all compost/device/lag candidates."""

    candidates: list[dict[str, Any]] = []

    for lag_h in range(lag_min, lag_max + 1):
        shifted = heat_wide.copy()
        shifted.index = shifted.index + pd.Timedelta(hours=lag_h)
        joined = env_hourly.join(shifted, how="inner")

        if len(joined) < min_overlap_hours:
            continue

        for compost in (1, 2):
            monitor_temp_col = f"temperatura_compost_{compost}"
            monitor_hum_col = f"humidade_compost_{compost}"

            for device in devices:
                temp_col = f"temperature_{device}"
                hum_col = f"humidity_{device}"
                if temp_col not in joined.columns or hum_col not in joined.columns:
                    continue

                corr_temp = safe_corr(joined[monitor_temp_col], joined[temp_col])
                corr_hum = safe_corr(joined[monitor_hum_col], joined[hum_col])
                mae_temp = mean_absolute_error(joined[monitor_temp_col], joined[temp_col])
                mae_hum = mean_absolute_error(joined[monitor_hum_col], joined[hum_col])
                score = mapping_score(corr_temp, corr_hum, mae_temp, mae_hum)

                candidates.append(
                    {
                        "compost": compost,
                        "device": int(device),
                        "lag_hours": int(lag_h),
                        "n_rows": int(len(joined)),
                        "corr_temp": corr_temp,
                        "corr_hum": corr_hum,
                        "mae_temp": mae_temp,
                        "mae_hum": mae_hum,
                        "score": score,
                        "valid_candidate": pd.notna(score),
                    }
                )

    audit_map = pd.DataFrame(candidates)
    if not audit_map.empty:
        audit_map = audit_map[audit_map["valid_candidate"]].copy()
    return audit_map


def _build_independent_lag_pairs(devices: list[int], audit_map: pd.DataFrame) -> pd.DataFrame:
    """Build candidate pairs allowing each compost to have its own best lag."""

    best_pairs: list[dict[str, Any]] = []

    for d1 in devices:
        rows1 = audit_map[(audit_map["compost"] == 1) & (audit_map["device"] == d1)]
        if rows1.empty:
            continue
        row1 = rows1.sort_values("score", ascending=False).iloc[0]

        for d2 in devices:
            if d2 == d1:
                continue
            rows2 = audit_map[(audit_map["compost"] == 2) & (audit_map["device"] == d2)]
            if rows2.empty:
                continue
            row2 = rows2.sort_values("score", ascending=False).iloc[0]

            best_pairs.append(_pair_row(row1, row2))

    return pd.DataFrame(best_pairs)


def _build_shared_lag_pairs(devices: list[int], audit_map: pd.DataFrame) -> pd.DataFrame:
    """Build candidate pairs forcing both composts to use the same lag."""

    best_pairs: list[dict[str, Any]] = []
    for lag_h in sorted(audit_map["lag_hours"].unique().tolist()):
        by_lag = audit_map[audit_map["lag_hours"] == lag_h]
        for d1 in devices:
            rows1 = by_lag[(by_lag["compost"] == 1) & (by_lag["device"] == d1)]
            if rows1.empty:
                continue
            row1 = rows1.sort_values("score", ascending=False).iloc[0]

            for d2 in devices:
                if d2 == d1:
                    continue
                rows2 = by_lag[(by_lag["compost"] == 2) & (by_lag["device"] == d2)]
                if rows2.empty:
                    continue
                row2 = rows2.sort_values("score", ascending=False).iloc[0]
                best_pairs.append(_pair_row(row1, row2))

    return pd.DataFrame(best_pairs)


def _pair_row(row1: pd.Series, row2: pd.Series) -> dict[str, Any]:
    """Create one pair-candidate row from selected compost rows."""

    return {
        "device_compost_1": int(row1["device"]),
        "lag_compost_1": int(row1["lag_hours"]),
        "score_compost_1": float(row1["score"]),
        "n_rows_compost_1": int(row1["n_rows"]),
        "device_compost_2": int(row2["device"]),
        "lag_compost_2": int(row2["lag_hours"]),
        "score_compost_2": float(row2["score"]),
        "n_rows_compost_2": int(row2["n_rows"]),
        "pair_score": float(row1["score"] + row2["score"]),
    }


def _build_uncertainty_report(
    audit_map: pd.DataFrame,
    device_map: dict[int, dict[str, int]],
    min_score_margin: float,
) -> dict[str, Any]:
    """Build uncertainty report based on score margin for selected compost mappings."""

    compost_quality: list[dict[str, Any]] = []
    for compost in (1, 2):
        rows = audit_map[audit_map["compost"] == compost].sort_values("score", ascending=False)
        best_score = float(rows.iloc[0]["score"]) if len(rows) >= 1 else float("nan")
        second_score = float(rows.iloc[1]["score"]) if len(rows) >= 2 else float("nan")
        margin = best_score - second_score if pd.notna(second_score) else float("nan")
        compost_quality.append(
            {
                "compost": compost,
                "selected_device": int(device_map[compost]["device"]),
                "selected_lag_hours": int(device_map[compost]["lag_hours"]),
                "best_score": best_score,
                "second_best_score": second_score,
                "score_margin": margin,
                "min_score_margin": float(min_score_margin),
                "low_score_margin": bool(pd.notna(margin) and margin < min_score_margin),
            }
        )

    return {"compost_quality": compost_quality}
