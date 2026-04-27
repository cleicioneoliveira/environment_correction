"""Input/output helpers for the environmental correction pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from .columns import (
    HEAT_REQUIRED_COLUMNS,
    MONITORAMENTO_REQUIRED_COLUMNS,
    normalize_columns,
    require_columns,
)
from .config import AppConfig


def ensure_output_dirs(config: AppConfig) -> None:
    """Create all parent directories required by configured output paths."""

    for path in (
        config.output_monitoramento,
        config.output_audit,
        config.output_pair_candidates,
        config.output_summary,
        config.output_quality,
        config.output_inconsistencies,
        config.output_coverage,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)


def _coerce_datetime_column(df: pd.DataFrame, column: str, df_name: str) -> pd.DataFrame:
    """Coerce a datetime column and fail with a clear message if it cannot be read."""

    df = df.copy()
    df[column] = pd.to_datetime(df[column], errors="coerce")
    invalid = int(df[column].isna().sum())
    if invalid == len(df):
        raise ValueError(f"A coluna de data '{column}' em {df_name} não pôde ser interpretada.")
    if invalid > 0:
        logging.getLogger("environment_correction").warning(
            "%s possui %s linhas com %s inválido; essas linhas podem não ser corrigidas.",
            df_name,
            invalid,
            column,
        )
    return df


def load_inputs(config: AppConfig, logger: logging.Logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read, normalize and validate the heat and monitoring input files.

    Parameters
    ----------
    config : AppConfig
        Runtime configuration.
    logger : logging.Logger
        Application logger.

    Returns
    -------
    tuple of pandas.DataFrame
        ``(heat, monitoramento)`` with normalized column names and datetime
        columns coerced.
    """

    logger.info("Lendo arquivo heat: %s", config.heat_path)
    heat = pd.read_csv(config.heat_path, low_memory=False)

    logger.info("Lendo arquivo monitoramento: %s", config.monitoramento_path)
    mon = pd.read_csv(config.monitoramento_path, low_memory=False)

    heat = normalize_columns(heat)
    mon = normalize_columns(mon)

    require_columns(heat, HEAT_REQUIRED_COLUMNS, "heat")
    require_columns(mon, MONITORAMENTO_REQUIRED_COLUMNS, "monitoramento")

    heat = _coerce_datetime_column(heat, "timestamp", "heat")
    mon = _coerce_datetime_column(mon, "data_hora", "monitoramento")

    return heat, mon


def save_outputs(
    config: AppConfig,
    monitor_corr: pd.DataFrame,
    audit_map: pd.DataFrame,
    best_pairs_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    inconsistencies_df: pd.DataFrame,
    coverage_df: pd.DataFrame,
    summary: dict[str, Any],
    logger: logging.Logger,
) -> None:
    """Save all pipeline artifacts to disk."""

    logger.info("Salvando monitoramento corrigido em: %s", config.output_monitoramento)
    monitor_corr.to_csv(config.output_monitoramento, index=False)

    logger.info("Salvando auditoria em: %s", config.output_audit)
    audit_map.to_csv(config.output_audit, index=False)

    logger.info("Salvando pares candidatos em: %s", config.output_pair_candidates)
    best_pairs_df.to_csv(config.output_pair_candidates, index=False)

    logger.info("Salvando sumário de qualidade em: %s", config.output_quality)
    quality_df.to_csv(config.output_quality, index=False)

    logger.info("Salvando inconsistências ambientais em: %s", config.output_inconsistencies)
    inconsistencies_df.to_csv(config.output_inconsistencies, index=False)

    logger.info("Salvando cobertura da correção em: %s", config.output_coverage)
    coverage_df.to_csv(config.output_coverage, index=False)

    logger.info("Salvando resumo JSON em: %s", config.output_summary)
    with config.output_summary.open("w", encoding="utf-8") as file_obj:
        json.dump(summary, file_obj, indent=2, ensure_ascii=False)
