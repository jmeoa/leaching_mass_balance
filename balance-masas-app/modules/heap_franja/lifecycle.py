"""Estados operacionales de franjas del pad horizontal."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from modules.heap_franja.models import Franja, HeapFranjaDataset


def infer_franja_state(franja: Franja, reference_date: pd.Timestamp | None = None) -> str:
    """Infiere el estado de una franja a una fecha de referencia."""
    if reference_date is None:
        reference_date = pd.Timestamp.now().normalize()
    else:
        reference_date = pd.Timestamp(reference_date).tz_localize(None) if pd.Timestamp(reference_date).tzinfo else pd.Timestamp(reference_date)
    if not franja.operativa:
        return "preparacion"
    if franja.fecha_on is None:
        return "apilando"
    fecha_on = pd.Timestamp(franja.fecha_on).tz_localize(None) if pd.Timestamp(franja.fecha_on).tzinfo else pd.Timestamp(franja.fecha_on)
    fecha_off = None
    if franja.fecha_off:
        fecha_off = pd.Timestamp(franja.fecha_off).tz_localize(None) if pd.Timestamp(franja.fecha_off).tzinfo else pd.Timestamp(franja.fecha_off)
    if fecha_on > reference_date:
        return "apilando"
    if fecha_off and fecha_off < reference_date:
        return "agotada"
    if fecha_off and (fecha_off - reference_date).days <= 10:
        return "drenando"
    return "regando"


def build_lifecycle_frame(dataset: HeapFranjaDataset, cycle_id: str) -> pd.DataFrame:
    """Construye una tabla de estados por franja."""
    records: List[Dict[str, object]] = []
    for franja in dataset.get_franjas_by_ciclo(cycle_id, operativas_only=False):
        records.append(
            {
                "id_franja": franja.id_franja,
                "numero_franja": franja.numero_franja,
                "estado": infer_franja_state(franja),
                "fecha_on": str(franja.fecha_on) if franja.fecha_on else None,
                "fecha_off": str(franja.fecha_off) if franja.fecha_off else None,
                "operativa": franja.operativa,
            }
        )
    return pd.DataFrame(records).sort_values("numero_franja").reset_index(drop=True)
