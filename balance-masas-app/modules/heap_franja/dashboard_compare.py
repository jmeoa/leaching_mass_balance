"""Payload comparativo entre franjas de un mismo ciclo."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from modules.heap_franja.aggregation import aggregate_cycle_results


def build_compare_payload(dataset, analysis_by_franja, cycle_id: str, franja_ids: Optional[Iterable[str]] = None) -> Dict[str, object]:
    """Arma una tabla comparativa entre franjas."""
    cycle_df = aggregate_cycle_results(dataset, analysis_by_franja, cycle_id)
    if franja_ids:
        cycle_df = cycle_df[cycle_df["id_franja"].isin(list(franja_ids))].copy()
    return {
        "rows": cycle_df.to_dict("records"),
        "bestRecovery": cycle_df.sort_values("recovery_pct", ascending=False).head(1).to_dict("records"),
        "highestAcidClosure": cycle_df.sort_values("acid_cierre_pct", ascending=False).head(1).to_dict("records"),
    }
