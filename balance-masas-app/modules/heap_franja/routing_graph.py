"""Construcción de nodos y enlaces para Sankey de ruteo."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from modules.heap_franja.models import HeapFranjaDataset


def build_cycle_routing_sankey(dataset: HeapFranjaDataset, cycle_id: str) -> Dict[str, List[Dict[str, object]]]:
    """Construye un Sankey simple refino/ILS → franjas."""
    cycle_franjas = {franja.id_franja for franja in dataset.get_franjas_by_ciclo(cycle_id, operativas_only=True)}
    riego_df = dataset.riego_df[dataset.riego_df["id_franja"].isin(cycle_franjas)].copy()
    if riego_df.empty:
        return {"nodes": [], "links": []}

    riego_df["source"] = riego_df["fuente_ils"].fillna("Refino SX")
    grouped = riego_df.groupby(["source", "id_franja"], as_index=False)["vol_aplicado_m3"].sum()

    node_labels = ["Refino SX"] + sorted({*grouped["source"].tolist(), *grouped["id_franja"].tolist()})
    nodes = [{"id": label, "label": label} for label in dict.fromkeys(node_labels)]
    links = [
        {
            "source": row["source"],
            "target": row["id_franja"],
            "value": round(float(row["vol_aplicado_m3"]), 2),
        }
        for _, row in grouped.iterrows()
    ]
    return {"nodes": nodes, "links": links}
