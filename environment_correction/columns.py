"""Column names and column validation helpers."""

from __future__ import annotations

import unicodedata

import pandas as pd

HEAT_REQUIRED_COLUMNS = ["timestamp", "dispositivo", "temperature", "humidity"]

ENVIRONMENT_COLUMNS = [
    "temperatura_compost_1",
    "humidade_compost_1",
    "thi_compost1",
    "temperatura_compost_2",
    "humidade_compost_2",
    "thi_compost2",
]

MONITORAMENTO_REQUIRED_COLUMNS = ["data_hora", *ENVIRONMENT_COLUMNS]


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
