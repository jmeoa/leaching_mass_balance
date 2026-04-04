"""Balance mensual de extracción por solventes (2E + 1S)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from config import DEFAULT_CONFIG


@dataclass(frozen=True)
class SolventExtractionMonthlyResult:
    periodo: str
    cu_acuoso_cargado_kg: float
    cu_raffinate_kg: float
    cu_transferido_extraccion_kg: float
    cu_transferido_stripping_kg: float
    cu_transferido_kg: float
    recuperacion_sx_pct: float
    oa_ratio: float
    acid_generado_extraccion_kg: float
    acid_consumido_stripping_kg: float


def calculate_sx_history(monthly_input_df: pd.DataFrame) -> pd.DataFrame:
    """Calcula KPIs mensuales de SX."""
    rows: List[Dict[str, float]] = []
    factor_acid = DEFAULT_CONFIG.factores.acid_por_cu

    for record in monthly_input_df.sort_values("periodo").to_dict("records"):
        cu_acuoso_cargado_kg = float(record["vol_acuoso_cargado_m3"]) * float(record["cu_acuoso_cargado_gpl"])
        cu_raffinate_kg = float(record["vol_refino_m3"]) * float(record["cu_refino_gpl"])
        cu_transferido_extraccion_kg = max(cu_acuoso_cargado_kg - cu_raffinate_kg, 0.0)
        cu_transferido_stripping_kg = max(
            (float(record["cu_electrolito_rico_gpl"]) - float(record["cu_electrolito_pobre_gpl"]))
            * float(record["vol_electrolito_rico_m3"]),
            0.0,
        )
        cu_transferido_kg = min(cu_transferido_extraccion_kg, cu_transferido_stripping_kg or cu_transferido_extraccion_kg)
        acid_generado_extraccion_kg = cu_transferido_kg * factor_acid
        acid_consumido_stripping_kg = max(
            (float(record["acid_electrolito_pobre_gpl"]) - float(record["acid_electrolito_rico_gpl"]))
            * float(record["vol_electrolito_rico_m3"]),
            0.0,
        )
        rows.append(
            SolventExtractionMonthlyResult(
                periodo=str(pd.Timestamp(record["periodo"]).strftime("%Y-%m")),
                cu_acuoso_cargado_kg=cu_acuoso_cargado_kg,
                cu_raffinate_kg=cu_raffinate_kg,
                cu_transferido_extraccion_kg=cu_transferido_extraccion_kg,
                cu_transferido_stripping_kg=cu_transferido_stripping_kg,
                cu_transferido_kg=cu_transferido_kg,
                recuperacion_sx_pct=(cu_transferido_kg / cu_acuoso_cargado_kg * 100.0) if cu_acuoso_cargado_kg > 0 else 0.0,
                oa_ratio=(float(record["vol_electrolito_rico_m3"]) / float(record["vol_acuoso_cargado_m3"]))
                if float(record["vol_acuoso_cargado_m3"]) > 0
                else 0.0,
                acid_generado_extraccion_kg=acid_generado_extraccion_kg,
                acid_consumido_stripping_kg=acid_consumido_stripping_kg,
            ).__dict__
        )

    return pd.DataFrame(rows)
