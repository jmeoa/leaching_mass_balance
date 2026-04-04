"""Validaciones y alertas del motor por franja/ciclo."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from config import DEFAULT_CONFIG


def build_franja_alerts(franja, copper_summary, acid_summary, rl_summary, module_metrics_df: pd.DataFrame) -> List[Dict[str, object]]:
    """Genera alertas operacionales simples para una franja."""
    alerts: List[Dict[str, object]] = []
    params = DEFAULT_CONFIG.parametros

    if copper_summary.recovery_pct < 50:
        alerts.append({"level": "warning", "title": "Recuperación baja", "message": "La recuperación está bajo 50%."})
    if acid_summary.acid_cierre_pct < 70:
        alerts.append({"level": "warning", "title": "Cierre ácido bajo", "message": "El balance de ácido no alcanza 70%."})
    if acid_summary.acid_no_asignado_kg > acid_summary.acid_consumido_total_kg * params.umbral_acid_no_asignado_pct / 100.0:
        alerts.append({"level": "warning", "title": "Ácido no asignado alto", "message": "Hay una fracción importante de consumo no explicada."})
    if not module_metrics_df.empty:
        worst = module_metrics_df["uniformidad_ratio"].min()
        if worst < 0.8:
            alerts.append({"level": "info", "title": "Riego poco uniforme", "message": f"Uniformidad mínima observada: {worst:.2f}."})
    if not alerts:
        alerts.append({"level": "ok", "title": "Sin alertas críticas", "message": "La franja está dentro de bandas operacionales."})
    return alerts


def build_cycle_alerts(summary_df: pd.DataFrame) -> List[Dict[str, object]]:
    """Alertas agregadas por ciclo."""
    alerts: List[Dict[str, object]] = []
    if summary_df.empty:
        return [{"level": "info", "title": "Sin datos", "message": "No hay franjas operativas en el ciclo."}]
    if (summary_df["recovery_pct"] < 50).any():
        alerts.append({"level": "warning", "title": "Franjas con baja recuperación", "message": "Al menos una franja cae bajo el umbral de 50%."})
    if (summary_df["acid_cierre_pct"] < 70).any():
        alerts.append({"level": "warning", "title": "Franjas con cierre ácido débil", "message": "Al menos una franja no supera 70% de cierre."})
    if not alerts:
        alerts.append({"level": "ok", "title": "Ciclo estable", "message": "Las franjas operativas cumplen las bandas objetivo."})
    return alerts
