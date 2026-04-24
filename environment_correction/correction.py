"""Correction routines for monitoring environmental variables."""

from __future__ import annotations

import logging

import pandas as pd

from .thi import thi_cattle


def build_corrected_environment(
    heat_hourly: pd.DataFrame,
    env_hourly: pd.DataFrame,
    device_map: dict[int, dict[str, int]],
    logger: logging.Logger,
) -> pd.DataFrame:
    """Build the corrected hourly environmental table.

    The returned table contains one row per monitoring hour and corrected
    temperature, humidity and THI columns for compost 1 and compost 2. Source
    values come from the selected heat device after the selected lag is applied.

    Parameters
    ----------
    heat_hourly : pandas.DataFrame
        Hourly heat data with columns ``data_hora_bruta``, ``dispositivo``,
        ``temperature`` and ``humidity``.
    env_hourly : pandas.DataFrame
        Monitoring environmental table indexed by ``data_hora``. Only its index
        is used to define the correction target hours.
    device_map : dict
        Mapping with keys ``1`` and ``2`` containing selected ``device`` and
        ``lag_hours``.
    logger : logging.Logger
        Application logger.

    Returns
    -------
    pandas.DataFrame
        Corrected hourly environmental table.
    """

    logger.info("Construindo ambiente horário corrigido")
    corrected_env = env_hourly.reset_index()[["data_hora"]].copy()

    for compost in (1, 2):
        device = device_map[compost]["device"]
        lag_h = device_map[compost]["lag_hours"]

        src = heat_hourly[heat_hourly["dispositivo"] == device].copy()
        src["data_hora"] = src["data_hora_bruta"] + pd.Timedelta(hours=lag_h)
        src = src.rename(
            columns={
                "temperature": f"temperatura_compost_{compost}_corrigida",
                "humidity": f"humidade_compost_{compost}_corrigida",
            }
        )[
            [
                "data_hora",
                f"temperatura_compost_{compost}_corrigida",
                f"humidade_compost_{compost}_corrigida",
            ]
        ]

        corrected_env = corrected_env.merge(src, on="data_hora", how="left")
        corrected_env[f"thi_compost{compost}_corrigido"] = thi_cattle(
            corrected_env[f"temperatura_compost_{compost}_corrigida"],
            corrected_env[f"humidade_compost_{compost}_corrigida"],
        )

    return corrected_env


def apply_correction(
    mon: pd.DataFrame,
    corrected_env: pd.DataFrame,
    logger: logging.Logger,
) -> pd.DataFrame:
    """Apply corrected environmental variables to the monitoring file.

    Only the six final environmental columns are replaced. All original columns
    and their order are preserved. When no corrected value is available for a
    given hour, the original value is kept.

    Parameters
    ----------
    mon : pandas.DataFrame
        Original monitoring DataFrame.
    corrected_env : pandas.DataFrame
        Corrected hourly environmental table.
    logger : logging.Logger
        Application logger.

    Returns
    -------
    pandas.DataFrame
        Corrected monitoring DataFrame with the same column structure as the
        input monitoring file.
    """

    logger.info("Aplicando correção no monitoramento")
    original_columns = mon.columns.tolist()

    merge_cols = [
        "data_hora",
        "temperatura_compost_1_corrigida",
        "humidade_compost_1_corrigida",
        "thi_compost1_corrigido",
        "temperatura_compost_2_corrigida",
        "humidade_compost_2_corrigida",
        "thi_compost2_corrigido",
    ]

    monitor_corr = mon.merge(corrected_env[merge_cols], on="data_hora", how="left")

    for compost in (1, 2):
        monitor_corr[f"temperatura_compost_{compost}"] = monitor_corr[
            f"temperatura_compost_{compost}_corrigida"
        ].combine_first(monitor_corr[f"temperatura_compost_{compost}"])

        monitor_corr[f"humidade_compost_{compost}"] = monitor_corr[
            f"humidade_compost_{compost}_corrigida"
        ].combine_first(monitor_corr[f"humidade_compost_{compost}"])

        monitor_corr[f"thi_compost{compost}"] = monitor_corr[
            f"thi_compost{compost}_corrigido"
        ].round(2).combine_first(monitor_corr[f"thi_compost{compost}"])

    return monitor_corr[original_columns]
