"""Reconciliación de franja entre soluciones, sólidos y alertas básicas."""

from __future__ import annotations

from typing import Dict


def build_reconciliation_summary(franja, copper_summary, acid_summary, rl_summary) -> Dict[str, object]:
    """Resume consistencia metalúrgica de una franja."""
    return {
        "id_franja": franja.id_franja,
        "recovery_direct_pct": float(copper_summary.recovery_direct_pct),
        "recovery_reconciled_pct": float(copper_summary.recovery_pct),
        "recovery_gap_pct_points": float(copper_summary.recovery_gap_pct_points or 0.0),
        "acid_cierre_pct": float(acid_summary.acid_cierre_pct),
        "acid_ratio_kgkg": float(acid_summary.ratio_acid_cu_kgkg),
        "rl_total_m3_t": float(rl_summary.rl_total_m3_t),
        "fase_dominante": rl_summary.fase_dominante_global,
        "status": "ok"
        if acid_summary.acid_cierre_pct >= 70 and copper_summary.recovery_pct >= 50
        else "warning",
    }
