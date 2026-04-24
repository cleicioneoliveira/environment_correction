"""Top-level pipeline orchestration for environmental correction."""

from __future__ import annotations

from typing import Any

from .alignment import infer_mapping
from .config import AppConfig
from .correction import apply_correction, build_corrected_environment
from .io import ensure_output_dirs, load_inputs, save_outputs
from .logging_utils import setup_logging
from .preprocessing import build_hourly_environment, normalize_humidity
from .quality import build_coverage_summary, build_quality_summary, build_summary


def run(config: AppConfig) -> dict[str, Any]:
    """Execute the complete environmental correction pipeline.

    Parameters
    ----------
    config : AppConfig
        Runtime configuration.

    Returns
    -------
    dict
        JSON-serializable execution summary.
    """

    logger = setup_logging(config.log_level)
    ensure_output_dirs(config)

    logger.info("Iniciando correção ambiental do monitoramento")
    heat, mon = load_inputs(config, logger)
    heat = normalize_humidity(heat, config.humidity_unit, logger)

    heat_hourly, heat_wide, env_hourly, inconsistencies_df = build_hourly_environment(
        heat=heat,
        mon=mon,
        aggregation=config.aggregation,
        logger=logger,
    )

    audit_map, best_pairs_df, device_map, uncertainty = infer_mapping(
        heat=heat,
        heat_wide=heat_wide,
        env_hourly=env_hourly,
        lag_min=config.lag_min,
        lag_max=config.lag_max,
        min_overlap_hours=config.min_overlap_hours,
        lag_mode=config.lag_mode,
        min_score_margin=config.min_score_margin,
        fail_on_low_quality=config.fail_on_low_quality,
        logger=logger,
    )

    corrected_env = build_corrected_environment(heat_hourly, env_hourly, device_map, logger)
    monitor_corr = apply_correction(mon, corrected_env, logger)
    quality_df = build_quality_summary(heat_hourly, env_hourly, device_map)
    coverage_df = build_coverage_summary(mon, corrected_env)

    parameters = {
        "lag_range": [config.lag_min, config.lag_max],
        "min_overlap_hours": config.min_overlap_hours,
        "lag_mode": config.lag_mode,
        "humidity_unit": config.humidity_unit,
        "aggregation": config.aggregation,
        "score_formula": "((corr_temp + corr_hum) / 2) - 0.01 * (mae_temp + mae_hum)",
        "min_score_margin": config.min_score_margin,
        "fail_on_low_quality": config.fail_on_low_quality,
    }

    summary = build_summary(
        heat=heat,
        mon=mon,
        mon_corr=monitor_corr,
        device_map=device_map,
        quality_df=quality_df,
        coverage_df=coverage_df,
        uncertainty=uncertainty,
        parameters=parameters,
    )

    save_outputs(
        config=config,
        monitor_corr=monitor_corr,
        audit_map=audit_map,
        best_pairs_df=best_pairs_df,
        quality_df=quality_df,
        inconsistencies_df=inconsistencies_df,
        coverage_df=coverage_df,
        summary=summary,
        logger=logger,
    )

    logger.info("Processo concluído com sucesso")
    return summary
