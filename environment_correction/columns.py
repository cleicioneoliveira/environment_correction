"""Column names and column validation helpers.

This module defines the canonical environmental column contract used by the
farm 1293 processing chain. Raw inputs may use different names, but this
package normalizes them before correction and exports stable column names to
be consumed by downstream repositories.
"""

from __future__ import annotations

from enum import StrEnum
import unicodedata

import pandas as pd


class HeatColumn(StrEnum):
    """Canonical columns expected in the heat_stress_report file."""

    TIMESTAMP = "timestamp"
    DEVICE = "dispositivo"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"


class MonitoramentoColumn(StrEnum):
    """Canonical monitoring columns used throughout the chain."""

    ANIMAL_ID = "brinco"
    DATA_HORA = "data_hora"

    TEMPERATURA_COMPOST_1 = "temperatura_compost_1"
    HUMIDADE_COMPOST_1 = "humidade_compost_1"
    THI_COMPOST_1 = "thi_compost1"
    TEMPERATURA_COMPOST_2 = "temperatura_compost_2"
    HUMIDADE_COMPOST_2 = "humidade_compost_2"
    THI_COMPOST_2 = "thi_compost2"


class IntegratedColumn(StrEnum):
    """Recommended final columns after monitoring/health integration."""

    ANIMAL_ID = "brinco"
    DATA_HORA = "data_hora"
    STATUS_SAUDE = "status_saude"
    OFEGACAO_HORA = "ofegacao_hora"


HEAT_REQUIRED_COLUMNS = [item.value for item in HeatColumn]

ENVIRONMENT_COLUMNS = [
    MonitoramentoColumn.TEMPERATURA_COMPOST_1.value,
    MonitoramentoColumn.HUMIDADE_COMPOST_1.value,
    MonitoramentoColumn.THI_COMPOST_1.value,
    MonitoramentoColumn.TEMPERATURA_COMPOST_2.value,
    MonitoramentoColumn.HUMIDADE_COMPOST_2.value,
    MonitoramentoColumn.THI_COMPOST_2.value,
]

MONITORAMENTO_REQUIRED_COLUMNS = [
    MonitoramentoColumn.DATA_HORA.value,
    *ENVIRONMENT_COLUMNS,
]

COLUMN_ALIASES: dict[str, str] = {
    "timestamp": HeatColumn.TIMESTAMP.value,
    "data": HeatColumn.TIMESTAMP.value,
    "data_hora": MonitoramentoColumn.DATA_HORA.value,
    "datetime": MonitoramentoColumn.DATA_HORA.value,
    "device": HeatColumn.DEVICE.value,
    "sensor": HeatColumn.DEVICE.value,
    "temperatura": HeatColumn.TEMPERATURE.value,
    "temperature": HeatColumn.TEMPERATURE.value,
    "umidade": HeatColumn.HUMIDITY.value,
    "humidity": HeatColumn.HUMIDITY.value,
}


def normalize_col(name: str) -> str:
    """Normalize a column name to a simple, ASCII, snake-like form.

    Parameters
    ----------
    name : str
        Original column name.

    Returns
    -------
    str
        Normalized name.
    """

    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    return (
        s.strip()
        .lower()
        .replace(" ", "_")
        .replace(".", "")
        .replace("/", "_")
        .replace("-", "_")
    )


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column names and apply known aliases."""
    normalized = df.copy()
    normalized.columns = [normalize_col(column) for column in normalized.columns]
    rename_map = {
        column: COLUMN_ALIASES[column]
        for column in normalized.columns
        if column in COLUMN_ALIASES and COLUMN_ALIASES[column] not in normalized.columns
    }
    if rename_map:
        normalized = normalized.rename(columns=rename_map)
    return normalized


def require_columns(df: pd.DataFrame, required: list[str], df_name: str) -> None:
    """Validate that required columns are present in a DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame to validate.
    required : list of str
        Required normalized column names.
    df_name : str
        Human-readable DataFrame name used in the error message.

    Raises
    ------
    ValueError
        If one or more required columns are missing.
    """

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes em {df_name}: {missing}")
