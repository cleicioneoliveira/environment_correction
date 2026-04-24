"""Preprocessing routines for heat and monitoring data."""

from __future__ import annotations

import logging

import pandas as pd

from .columns import ENVIRONMENT_COLUMNS
from .config import AggregationMethod, HumidityUnit


def normalize_humidity(
    heat: pd.DataFrame,
    humidity_unit: HumidityUnit,
    logger: logging.Logger,
) -> pd.DataFrame:
    """Normalize heat relative humidity to percentage.

    Parameters
    ----------
    heat : pandas.DataFrame
        Heat input data with a ``humidity`` column.
    humidity_unit : {'auto', 'pct', 'fraction'}
        Declared humidity unit.
    logger : logging.Logger
        Application logger.

    Returns
    -------
    pandas.DataFrame
        Copy of ``heat`` with humidity in percentage.
    """

    heat = heat.copy()
    valid = pd.to_numeric(heat["humidity"], errors="coerce")
    heat["humidity"] = valid

    if humidity_unit == "fraction":
        logger.info("Convertendo umidade do heat de fração [0,1] para porcentagem [0,100].")
        heat["humidity"] = heat["humidity"] * 100
        return heat

    if humidity_unit == "pct":
        return heat

    max_h = heat["humidity"].max(skipna=True)
    min_h = heat["humidity"].min(skipna=True)

    if pd.notna(max_h) and max_h <= 1.5 and pd.notna(min_h) and min_h >= 0:
        logger.warning(
            "Umidade do heat parece estar em fração [0,1]. Convertendo automaticamente para porcentagem."
        )
        heat["humidity"] = heat["humidity"] * 100
    return heat


def build_hourly_environment(
    heat: pd.DataFrame,
    mon: pd.DataFrame,
    aggregation: AggregationMethod,
    logger: logging.Logger,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build hourly heat, wide heat, monitoring environment and inconsistency report.

    The monitoring file usually contains repeated rows per hour because several
    animals share the same environmental measurement. The correction logic needs
    one environmental row per hour, but before collapsing those rows this
    function audits whether repeated values are truly consistent.

    Parameters
    ----------
    heat : pandas.DataFrame
        Heat input data.
    mon : pandas.DataFrame
        Monitoring input data.
    aggregation : {'mean', 'median'}
        Hourly aggregation method for heat data.
    logger : logging.Logger
        Application logger.

    Returns
    -------
    tuple
        ``(heat_hourly, heat_wide, env_hourly, inconsistencies_df)``.
    """

    logger.info("Construindo agregação horária do arquivo heat usando método: %s", aggregation)

    heat = heat.copy()
    heat["temperature"] = pd.to_numeric(heat["temperature"], errors="coerce")
    heat["humidity"] = pd.to_numeric(heat["humidity"], errors="coerce")
    heat["dispositivo"] = pd.to_numeric(heat["dispositivo"], errors="coerce")
    heat = heat.dropna(subset=["timestamp", "dispositivo", "temperature", "humidity"])
    heat["dispositivo"] = heat["dispositivo"].astype(int)
    heat["data_hora_bruta"] = heat["timestamp"].dt.floor("h")

    agg_func = "mean" if aggregation == "mean" else "median"
    heat_hourly = (
        heat.groupby(["data_hora_bruta", "dispositivo"], as_index=False)[["temperature", "humidity"]]
        .agg(agg_func)
        .sort_values(["data_hora_bruta", "dispositivo"])
    )

    heat_wide = heat_hourly.pivot(
        index="data_hora_bruta",
        columns="dispositivo",
        values=["temperature", "humidity"],
    )
    heat_wide.columns = [f"{metric}_{device}" for metric, device in heat_wide.columns]
    heat_wide = heat_wide.sort_index()

    inconsistencies_df = audit_hourly_environment_inconsistencies(mon, logger)

    env_hourly = (
        mon.groupby("data_hora", as_index=False)[ENVIRONMENT_COLUMNS]
        .first()
        .sort_values("data_hora")
        .set_index("data_hora")
    )

    logger.info(
        "Agregação horária concluída: %s linhas heat-hourly, %s horários no monitoramento.",
        len(heat_hourly),
        len(env_hourly),
    )
    return heat_hourly, heat_wide, env_hourly, inconsistencies_df


def audit_hourly_environment_inconsistencies(
    mon: pd.DataFrame,
    logger: logging.Logger,
) -> pd.DataFrame:
    """Detect inconsistent environmental values among rows sharing the same hour.

    Returns one row per ``data_hora`` and variable where the monitoring file has
    more than one distinct non-null value.
    """

    rows: list[dict] = []
    for col in ENVIRONMENT_COLUMNS:
        grouped = mon.groupby("data_hora")[col]
        nunique = grouped.nunique(dropna=True)
        problematic_times = nunique[nunique > 1].index
        for timestamp in problematic_times:
            values = sorted(mon.loc[mon["data_hora"] == timestamp, col].dropna().unique().tolist())
            rows.append(
                {
                    "data_hora": timestamp,
                    "column": col,
                    "n_distinct_values": int(len(values)),
                    "values": ";".join(map(str, values[:20])),
                }
            )

    inconsistencies_df = pd.DataFrame(rows)
    if inconsistencies_df.empty:
        logger.info("Nenhuma inconsistência ambiental horária encontrada no monitoramento.")
    else:
        logger.warning(
            "Foram encontradas %s inconsistências ambientais horárias no monitoramento.",
            len(inconsistencies_df),
        )
    return inconsistencies_df
