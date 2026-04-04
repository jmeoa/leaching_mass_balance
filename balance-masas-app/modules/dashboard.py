"""Builders de payload para la UI React."""

from __future__ import annotations

import json
from typing import Any, Dict

import pandas as pd

from modules.data_loader import get_default_monthly_input
from modules.electrowinning import calculate_ew_history
from modules.leaching import calculate_leaching_history
from modules.mass_balance import calculate_global_balance
from modules.solvent_extraction import calculate_sx_history


def build_dashboard_bundle(monthly_input_df: pd.DataFrame | None = None) -> Dict[str, Any]:
    """Construye el bundle principal para la vista mensual."""
    raw_df = monthly_input_df.copy() if monthly_input_df is not None else get_default_monthly_input()
    leaching_df = calculate_leaching_history(raw_df)
    sx_df = calculate_sx_history(raw_df)
    ew_df = calculate_ew_history(raw_df)
    global_df, summary = calculate_global_balance(raw_df)

    periods = [str(value) for value in global_df["periodo"].tolist()]
    overview_cards = [
        {"label": "Cu alimentado total", "value": f"{summary['cu_alimentado_total_t']:.1f} t", "tone": "copper"},
        {"label": "Cu cátodos total", "value": f"{summary['cu_catodos_total_t']:.1f} t", "tone": "water"},
        {"label": "Recuperación global", "value": f"{summary['recuperacion_global_pct']:.1f}%", "tone": "slate"},
        {"label": "Ácido makeup", "value": f"{summary['acid_makeup_total_t']:.1f} t", "tone": "acid"},
    ]

    trends = {
        "periods": periods,
        "cuAlimentadoT": (global_df["cu_alimentado_kg"] / 1000.0).round(2).tolist(),
        "cuCatodosT": (global_df["cu_depositado_kg"] / 1000.0).round(2).tolist(),
        "recuperacionLixPct": leaching_df["recuperacion_lix_pct"].round(2).tolist(),
        "recuperacionSxPct": sx_df["recuperacion_sx_pct"].round(2).tolist(),
        "recuperacionEwPct": ew_df["recuperacion_ew_pct"].round(2).tolist(),
        "recuperacionGlobalPct": global_df["recuperacion_global_pct"].round(2).tolist(),
        "acidNetoKgKg": global_df["consumo_neto_acido_kgkg"].round(3).tolist(),
        "inventarioCuT": (leaching_df["inventario_cu_kg"] / 1000.0).round(2).tolist(),
    }

    latest_inventory_raw = raw_df.sort_values("periodo").iloc[-1]["pilas_activas_inventario"]
    latest_inventory = json.loads(latest_inventory_raw) if isinstance(latest_inventory_raw, str) else latest_inventory_raw

    return {
        "summary": summary,
        "cards": overview_cards,
        "trends": trends,
        "tables": {
            "raw": raw_df.assign(periodo=raw_df["periodo"].dt.strftime("%Y-%m")).to_dict("records"),
            "global": global_df.to_dict("records"),
            "leaching": leaching_df.to_dict("records"),
            "sx": sx_df.to_dict("records"),
            "ew": ew_df.to_dict("records"),
        },
        "inventory": latest_inventory,
    }
