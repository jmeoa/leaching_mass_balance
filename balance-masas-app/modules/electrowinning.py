"""Cálculos mensuales de electro-obtención."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from config import DEFAULT_CONFIG


@dataclass(frozen=True)
class ElectrowinningMonthlyResult:
    periodo: str
    cu_disponible_kg: float
    cu_depositado_kg: float
    recuperacion_ew_pct: float
    eficiencia_corriente_pct: float
    acid_generado_ew_kg: float


def calculate_ew_history(monthly_input_df: pd.DataFrame) -> pd.DataFrame:
    """Calcula KPIs mensuales de EW."""
    rows: List[Dict[str, float]] = []
    factor_acid = DEFAULT_CONFIG.factores.acid_generado_ew

    for record in monthly_input_df.sort_values("periodo").to_dict("records"):
        cu_disponible_kg = max(
            (
                float(record["vol_electrolito_rico_m3"]) * float(record["cu_electrolito_rico_gpl"])
                - float(record["vol_electrolito_pobre_m3"]) * float(record["cu_electrolito_pobre_gpl"])
            ),
            0.0,
        )
        cu_depositado_kg = float(record["catodos_ton"]) * 1000.0
        rows.append(
            ElectrowinningMonthlyResult(
                periodo=str(pd.Timestamp(record["periodo"]).strftime("%Y-%m")),
                cu_disponible_kg=cu_disponible_kg,
                cu_depositado_kg=cu_depositado_kg,
                recuperacion_ew_pct=(cu_depositado_kg / cu_disponible_kg * 100.0) if cu_disponible_kg > 0 else 0.0,
                eficiencia_corriente_pct=float(record["eficiencia_corriente"]),
                acid_generado_ew_kg=cu_depositado_kg * factor_acid,
            ).__dict__
        )

    return pd.DataFrame(rows)
