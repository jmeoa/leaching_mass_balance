"""Payloads para la vista general del pad."""

from __future__ import annotations

from typing import Dict

from modules.heap_franja.aggregation import aggregate_cycle_results
from modules.heap_franja.lifecycle import build_lifecycle_frame
from modules.heap_franja.routing_graph import build_cycle_routing_sankey
from modules.heap_franja.validators import build_cycle_alerts


def build_pad_dashboard_payload(dataset, analysis_by_franja, cycle_id: str) -> Dict[str, object]:
    """Compone el payload principal de la vista pad."""
    cycle_df = aggregate_cycle_results(dataset, analysis_by_franja, cycle_id)
    lifecycle_df = build_lifecycle_frame(dataset, cycle_id)
    return {
        "cycleSummary": cycle_df.to_dict("records"),
        "lifecycle": lifecycle_df.to_dict("records"),
        "sankey": build_cycle_routing_sankey(dataset, cycle_id),
        "alerts": build_cycle_alerts(cycle_df),
    }
