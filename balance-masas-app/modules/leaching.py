"""Cálculos mensuales de lixiviación e inventario de pilas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd


@dataclass(frozen=True)
class LeachingMonthlyResult:
    periodo: str
    mineral_alimentado_ton: float
    ley_cu_alimentada_pct: float
    cu_alimentado_kg: float
    cu_extraido_pls_kg: float
    cu_refino_kg: float
    recuperacion_lix_pct: float
    inventario_cu_kg: float
    acid_consumido_lix_kg: float
    acid_consumo_neto_kgkg: float
    pilas_activas: int
    cu_remanente_activo_kg: float


def parse_pile_inventory(value: Any) -> List[Dict[str, Any]]:
    """Parsea el inventario serializado de pilas."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def calculate_leaching_history(monthly_input_df: pd.DataFrame) -> pd.DataFrame:
    """Calcula KPIs mensuales de la etapa LIX."""
    rows: List[Dict[str, Any]] = []
    inventory_prev_kg = 0.0

    for record in monthly_input_df.sort_values("periodo").to_dict("records"):
        cu_alimentado_kg = float(record["mineral_alimentado_ton"]) * 1000.0 * float(record["ley_cu_alimentada"]) / 100.0
        cu_extraido_pls_kg = float(record["vol_pls_m3"]) * float(record["cu_pls_gpl"])
        cu_refino_kg = float(record["vol_refino_m3"]) * float(record["cu_refino_gpl"])
        acid_refino_kg = float(record["vol_refino_m3"]) * float(record["acid_refino_gpl"])
        acid_pls_kg = float(record["vol_pls_m3"]) * float(record["acid_pls_gpl"])
        acid_consumido_lix_kg = max(acid_refino_kg - acid_pls_kg, 0.0)
        inventory_cu_kg = inventory_prev_kg + cu_alimentado_kg - cu_extraido_pls_kg
        recovery_lix_pct = (cu_extraido_pls_kg / cu_alimentado_kg * 100.0) if cu_alimentado_kg > 0 else 0.0
        pile_inventory = parse_pile_inventory(record["pilas_activas_inventario"])
        cu_remanente_activo_kg = sum(float(pile.get("cu_remanente_t", 0.0)) for pile in pile_inventory) * 1000.0

        rows.append(
            LeachingMonthlyResult(
                periodo=str(pd.Timestamp(record["periodo"]).strftime("%Y-%m")),
                mineral_alimentado_ton=float(record["mineral_alimentado_ton"]),
                ley_cu_alimentada_pct=float(record["ley_cu_alimentada"]),
                cu_alimentado_kg=cu_alimentado_kg,
                cu_extraido_pls_kg=cu_extraido_pls_kg,
                cu_refino_kg=cu_refino_kg,
                recuperacion_lix_pct=recovery_lix_pct,
                inventario_cu_kg=inventory_cu_kg,
                acid_consumido_lix_kg=acid_consumido_lix_kg,
                acid_consumo_neto_kgkg=(acid_consumido_lix_kg / cu_extraido_pls_kg) if cu_extraido_pls_kg > 0 else 0.0,
                pilas_activas=len([pile for pile in pile_inventory if pile.get("estado") != "agotada"]),
                cu_remanente_activo_kg=cu_remanente_activo_kg,
            ).__dict__
        )
        inventory_prev_kg = inventory_cu_kg

    return pd.DataFrame(rows)
