"""Command-line interface for the environmental correction utility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import AppConfig
from .logging_utils import DEFAULT_LOG_LEVEL
from .pipeline import run


def existing_file(path_str: str) -> Path:
    """Convert a CLI argument to an existing absolute file path."""

    path = Path(path_str).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Arquivo não encontrado: {path}")
    return path


def output_path(path_str: str) -> Path:
    """Convert a CLI argument to an absolute output path."""

    return Path(path_str).expanduser().resolve()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        prog="environment-correction",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Corrige variáveis ambientais do monitoramento usando o heat_stress_report "
            "como fonte de verdade, com inferência auditável de dispositivo e lag horário."
        ),
    )

    parser.add_argument("--heat", required=True, type=existing_file, help="Arquivo heat_stress_report CSV.")
    parser.add_argument("--monitoramento", required=True, type=existing_file, help="Arquivo monitoramento CSV.")

    parser.add_argument("--output-dir", type=output_path, default=None, help="Diretório base de saída.")
    parser.add_argument("--output-monitoramento", type=output_path, default=None, help="CSV final corrigido.")
    parser.add_argument("--output-audit", type=output_path, default=None, help="CSV de auditoria de candidatos.")
    parser.add_argument("--output-pairs", type=output_path, default=None, help="CSV de pares candidatos.")
    parser.add_argument("--output-summary", type=output_path, default=None, help="JSON de resumo.")
    parser.add_argument("--output-quality", type=output_path, default=None, help="CSV de qualidade do mapeamento escolhido.")
    parser.add_argument(
        "--output-inconsistencies",
        type=output_path,
        default=None,
        help="CSV de inconsistências ambientais horárias no monitoramento.",
    )
    parser.add_argument("--output-coverage", type=output_path, default=None, help="CSV de cobertura da correção.")

    parser.add_argument("--lag-min", type=int, default=-6, help="Lag mínimo, em horas.")
    parser.add_argument("--lag-max", type=int, default=6, help="Lag máximo, em horas.")
    parser.add_argument(
        "--min-overlap-hours",
        type=int,
        default=24,
        help="Número mínimo de horas sobrepostas para avaliar cada candidato.",
    )
    parser.add_argument(
        "--lag-mode",
        choices=["independent", "shared"],
        default="independent",
        help="Estratégia de lag: independente por compost ou compartilhada.",
    )
    parser.add_argument(
        "--humidity-unit",
        choices=["auto", "pct", "fraction"],
        default="auto",
        help="Unidade da umidade relativa no heat.",
    )
    parser.add_argument(
        "--aggregation",
        choices=["mean", "median"],
        default="mean",
        help="Método de agregação horária do heat.",
    )
    parser.add_argument(
        "--min-score-margin",
        type=float,
        default=0.05,
        help="Margem mínima desejável entre primeiro e segundo candidato.",
    )
    parser.add_argument(
        "--fail-on-low-quality",
        action="store_true",
        help="Interrompe a execução se a margem de score for baixa.",
    )
    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Nível de log.",
    )

    return parser.parse_args()


def build_config(args: argparse.Namespace) -> AppConfig:
    """Build :class:`AppConfig` from parsed CLI arguments."""

    base_output_dir = args.output_dir or args.monitoramento.parent / "processado"
    base_output_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        heat_path=args.heat,
        monitoramento_path=args.monitoramento,
        output_monitoramento=args.output_monitoramento or base_output_dir / "monitoramento_full_corrigido.csv",
        output_audit=args.output_audit or base_output_dir / "device_lag_audit.csv",
        output_pair_candidates=args.output_pairs or base_output_dir / "device_pair_candidates.csv",
        output_summary=args.output_summary or base_output_dir / "correction_summary.json",
        output_quality=args.output_quality or base_output_dir / "quality_summary.csv",
        output_inconsistencies=args.output_inconsistencies or base_output_dir / "environment_inconsistencies.csv",
        output_coverage=args.output_coverage or base_output_dir / "correction_coverage.csv",
        log_level=args.log_level,
        lag_min=args.lag_min,
        lag_max=args.lag_max,
        min_overlap_hours=args.min_overlap_hours,
        lag_mode=args.lag_mode,
        humidity_unit=args.humidity_unit,
        aggregation=args.aggregation,
        min_score_margin=args.min_score_margin,
        fail_on_low_quality=args.fail_on_low_quality,
    )


def main() -> None:
    """CLI entry point."""

    args = parse_args()
    config = build_config(args)
    summary = run(config)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
