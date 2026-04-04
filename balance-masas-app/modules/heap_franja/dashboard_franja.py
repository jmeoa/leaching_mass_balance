"""Payloads detallados de una franja para la UI React."""

from __future__ import annotations

from typing import Dict

from modules.heap_franja.kinetics import build_recovery_vs_rl_curve
from modules.heap_franja.validators import build_franja_alerts


def build_franja_dashboard_payload(dataset, franja, analysis: Dict[str, object], cut_off_acid_cu: float) -> Dict[str, object]:
    """Compone el payload detallado de una franja."""
    recovery_curve = build_recovery_vs_rl_curve(analysis["copper_daily_df"], analysis["rl_daily_df"])
    acid_daily = analysis["acid_daily_df"][["fecha", "acid_consumido_kg", "acid_asignado_kg"]].copy()
    return {
        "franja": {
            "id": franja.id_franja,
            "numero": franja.numero_franja,
            "ciclo": franja.id_ciclo,
            "tonelaje_t": franja.tonelaje_t,
            "ley_cu_total_pct": franja.ley_cu_total_pct,
            "ley_cu_soluble_pct": franja.ley_cu_soluble_pct,
        },
        "copperSummary": analysis["copper_summary"].__dict__,
        "acidSummary": analysis["acid_summary"].__dict__,
        "rlSummary": analysis["rl_summary"].__dict__,
        "moduleMetrics": analysis["module_metrics_df"].to_dict("records"),
        "recoveryCurve": recovery_curve.to_dict("records"),
        "alerts": build_franja_alerts(
            franja,
            analysis["copper_summary"],
            analysis["acid_summary"],
            analysis["rl_summary"],
            analysis["module_metrics_df"],
        ),
        "daily": {
            "acid": acid_daily.to_dict("records"),
        },
    }
