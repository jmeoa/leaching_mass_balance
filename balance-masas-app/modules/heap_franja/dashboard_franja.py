"""Payloads detallados de una franja para la UI React."""

from __future__ import annotations

from typing import Dict

from modules.heap_franja.irrigation import (
    build_irrigation_timeline,
    build_routing_transitions,
    summarize_irrigation_sources,
)
from modules.heap_franja.kinetics import build_recovery_vs_rl_curve, project_cutoff_day
from modules.heap_franja.reconciliation import build_reconciliation_summary
from modules.heap_franja.validators import build_franja_alerts


def build_franja_dashboard_payload(dataset, franja, analysis: Dict[str, object], cut_off_acid_cu: float) -> Dict[str, object]:
    """Compone el payload detallado de una franja."""
    recovery_curve = build_recovery_vs_rl_curve(analysis["copper_daily_df"], analysis["rl_daily_df"])
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
        "irrigationTimeline": build_irrigation_timeline(dataset, franja.id_franja).to_dict("records"),
        "routingTransitions": build_routing_transitions(dataset, franja.id_franja).to_dict("records"),
        "sourceSummary": summarize_irrigation_sources(dataset, franja.id_franja).to_dict("records"),
        "recoveryCurve": recovery_curve.to_dict("records"),
        "cutoffProjection": project_cutoff_day(
            analysis["acid_daily_df"],
            analysis["copper_daily_df"],
            cut_off_acid_cu,
        ),
        "reconciliation": build_reconciliation_summary(
            franja,
            analysis["copper_summary"],
            analysis["acid_summary"],
            analysis["rl_summary"],
        ),
        "alerts": build_franja_alerts(
            franja,
            analysis["copper_summary"],
            analysis["acid_summary"],
            analysis["rl_summary"],
            analysis["module_metrics_df"],
        ),
        "daily": {
            "copper": analysis["copper_daily_df"].to_dict("records"),
            "acid": analysis["acid_daily_df"].to_dict("records"),
            "rl": analysis["rl_daily_df"].to_dict("records"),
        },
    }
