"""Servicios de aplicación para FastAPI."""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from openpyxl import Workbook

from modules.dashboard import build_dashboard_bundle
from modules.data_loader import (
    EXPECTED_MONTHLY_COLUMNS,
    build_synthetic_monthly_input,
    load_monthly_input_file,
    load_monthly_snapshot,
    persist_monthly_snapshot,
    validate_monthly_input,
)
from modules.electrowinning import calculate_ew_history
from modules.heap_franja import (
    HeapFranjaDataset,
    calculate_acid_balance,
    calculate_copper_balance,
    calculate_leach_ratio,
    calculate_weighted_input,
)
from modules.heap_franja.aggregation import aggregate_cycle_results
from modules.heap_franja.dashboard_compare import build_compare_payload
from modules.heap_franja.dashboard_franja import build_franja_dashboard_payload
from modules.heap_franja.dashboard_pad import build_pad_dashboard_payload
from modules.leaching import calculate_leaching_history
from modules.mass_balance import calculate_global_balance
from modules.reports import build_excel_report, build_pdf_report
from modules.sheets_backend import get_backend
from modules.solvent_extraction import calculate_sx_history


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "synthetic"
TEMPLATE_PATH = BASE_DIR / "templates" / "template_input.xlsx"


def dataframe_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Serializa DataFrames para JSON."""
    if df.empty:
        return []
    serializable = df.copy()
    for column in serializable.columns:
        if pd.api.types.is_datetime64_any_dtype(serializable[column]):
            serializable[column] = serializable[column].dt.strftime("%Y-%m-%d")
    return serializable.to_dict("records")


class BalanceService:
    """Fachada principal de dominio para la API."""

    def __init__(self) -> None:
        self.backend = get_backend()

    @lru_cache(maxsize=1)
    def get_heap_dataset(self) -> HeapFranjaDataset:
        return HeapFranjaDataset.from_csv_dir(DATA_DIR)

    def ensure_template_exists(self) -> Path:
        TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if TEMPLATE_PATH.exists():
            return TEMPLATE_PATH
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "template_input"
        worksheet.append(EXPECTED_MONTHLY_COLUMNS)
        example_df = build_synthetic_monthly_input().head(1).copy()
        if not example_df.empty:
            row = example_df.iloc[0].to_dict()
            row["periodo"] = pd.Timestamp(row["periodo"]).strftime("%Y-%m")
            worksheet.append([row.get(column, "") for column in EXPECTED_MONTHLY_COLUMNS])
        workbook.save(TEMPLATE_PATH)
        return TEMPLATE_PATH

    @lru_cache(maxsize=1)
    def get_monthly_input(self) -> pd.DataFrame:
        base_df = load_monthly_snapshot()
        if base_df.empty:
            base_df = build_synthetic_monthly_input()
            persist_monthly_snapshot(base_df)
        stored_df = self.backend.get_history()
        if stored_df.empty:
            return base_df
        merged = pd.concat([base_df, stored_df], ignore_index=True)
        merged["periodo"] = pd.to_datetime(merged["periodo"])
        merged = merged.drop_duplicates(subset=["periodo"], keep="last").sort_values("periodo")
        validated, _ = validate_monthly_input(merged)
        return validated

    @lru_cache(maxsize=1)
    def get_dashboard_bundle(self) -> Dict[str, Any]:
        monthly_input = self.get_monthly_input()
        return build_dashboard_bundle(monthly_input)

    @lru_cache(maxsize=32)
    def analyze_franja(self, franja_id: str) -> Dict[str, Any]:
        dataset = self.get_heap_dataset()
        franja = dataset.get_franja(franja_id)
        riego_df = dataset.get_riego_by_franja(franja_id)
        pls_df = dataset.get_pls_by_franja(franja_id)
        modulos_df = dataset.get_modulos_by_franja(franja_id)
        weighted_df = calculate_weighted_input(riego_df)
        copper_daily_df, copper_summary = calculate_copper_balance(
            franja,
            riego_df,
            pls_df,
            weighted_input_df=weighted_df,
        )
        acid_daily_df, acid_summary = calculate_acid_balance(
            franja,
            riego_df,
            pls_df,
            weighted_input_df=weighted_df,
            copper_daily_df=copper_daily_df,
        )
        rl_daily_df, rl_summary, module_metrics_df = calculate_leach_ratio(
            franja,
            riego_df,
            modulos_df,
            weighted_input_df=weighted_df,
        )
        return {
            "franja": franja,
            "weighted_df": weighted_df,
            "riego_df": riego_df,
            "pls_df": pls_df,
            "modulos_df": modulos_df,
            "copper_daily_df": copper_daily_df,
            "copper_summary": copper_summary,
            "acid_daily_df": acid_daily_df,
            "acid_summary": acid_summary,
            "rl_daily_df": rl_daily_df,
            "rl_summary": rl_summary,
            "module_metrics_df": module_metrics_df,
        }

    @lru_cache(maxsize=16)
    def analyze_cycle(self, cycle_id: str) -> Dict[str, Dict[str, Any]]:
        dataset = self.get_heap_dataset()
        if cycle_id not in dataset.ciclos:
            raise KeyError(f"Ciclo no encontrado: {cycle_id}")
        results: Dict[str, Dict[str, Any]] = {}
        for franja in dataset.get_franjas_by_ciclo(cycle_id, operativas_only=False):
            try:
                results[franja.id_franja] = self.analyze_franja(franja.id_franja)
            except Exception:
                continue
        return results

    def get_heap_meta(self) -> Dict[str, Any]:
        dataset = self.get_heap_dataset()
        return {
            "cycles": [
                {
                    "id": ciclo.id_ciclo,
                    "label": f"{ciclo.id_ciclo} · ciclo {ciclo.numero_ciclo} · {ciclo.estado}",
                    "estado": ciclo.estado,
                    "cutoff": ciclo.cut_off_acid_cu,
                }
                for ciclo in dataset.get_ciclos()
            ]
        }

    @lru_cache(maxsize=16)
    def get_cycle_summary(self, cycle_id: str) -> List[Dict[str, Any]]:
        dataset = self.get_heap_dataset()
        if cycle_id not in dataset.ciclos:
            raise KeyError(f"Ciclo no encontrado: {cycle_id}")
        cycle_df = aggregate_cycle_results(dataset, self.analyze_cycle(cycle_id), cycle_id)
        return dataframe_to_records(cycle_df)

    @lru_cache(maxsize=16)
    def get_pad_payload(self, cycle_id: str) -> Dict[str, Any]:
        dataset = self.get_heap_dataset()
        if cycle_id not in dataset.ciclos:
            raise KeyError(f"Ciclo no encontrado: {cycle_id}")
        return build_pad_dashboard_payload(dataset, self.analyze_cycle(cycle_id), cycle_id)

    @lru_cache(maxsize=64)
    def get_franja_payload(self, franja_id: str) -> Dict[str, Any]:
        dataset = self.get_heap_dataset()
        franja = dataset.get_franja(franja_id)
        cycle = dataset.get_ciclo(franja.id_ciclo)
        return build_franja_dashboard_payload(
            dataset,
            franja,
            self.analyze_franja(franja_id),
            cycle.cut_off_acid_cu,
        )

    @lru_cache(maxsize=32)
    def get_compare_payload(self, cycle_id: str, franja_ids: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        dataset = self.get_heap_dataset()
        if cycle_id not in dataset.ciclos:
            raise KeyError(f"Ciclo no encontrado: {cycle_id}")
        return build_compare_payload(dataset, self.analyze_cycle(cycle_id), cycle_id, franja_ids)

    def preview_upload(self, content: bytes, filename: str) -> Dict[str, Any]:
        df, issues = load_monthly_input_file(content, filename)
        return {
            "issues": issues,
            "preview": dataframe_to_records(df.head(12)),
            "rows": int(len(df)),
            "valid": not any(issue["level"] == "error" for issue in issues),
        }

    def process_upload(self, content: bytes, filename: str) -> Dict[str, Any]:
        df, issues = load_monthly_input_file(content, filename)
        if any(issue["level"] == "error" for issue in issues):
            return {"processed": False, "issues": issues, "rows": 0}
        for record in dataframe_to_records(df):
            self.backend.update_month(record["periodo"], record)
        if hasattr(self.get_monthly_input, "cache_clear"):
            self.get_monthly_input.cache_clear()
        if hasattr(self.get_dashboard_bundle, "cache_clear"):
            self.get_dashboard_bundle.cache_clear()
        if hasattr(self.get_reports_bundle, "cache_clear"):
            self.get_reports_bundle.cache_clear()
        if hasattr(self.analyze_cycle, "cache_clear"):
            self.analyze_cycle.cache_clear()
        if hasattr(self.get_cycle_summary, "cache_clear"):
            self.get_cycle_summary.cache_clear()
        if hasattr(self.get_pad_payload, "cache_clear"):
            self.get_pad_payload.cache_clear()
        if hasattr(self.get_franja_payload, "cache_clear"):
            self.get_franja_payload.cache_clear()
        if hasattr(self.get_compare_payload, "cache_clear"):
            self.get_compare_payload.cache_clear()
        return {"processed": True, "issues": issues, "rows": int(len(df))}

    @lru_cache(maxsize=16)
    def get_reports_bundle(self, period: Optional[str] = None) -> Dict[str, Any]:
        monthly_input = self.get_monthly_input()
        if period:
            period_ts = pd.Timestamp(period).to_period("M").to_timestamp()
            monthly_input = monthly_input[monthly_input["periodo"] == period_ts].copy()
        leaching_df = calculate_leaching_history(monthly_input)
        sx_df = calculate_sx_history(monthly_input)
        ew_df = calculate_ew_history(monthly_input)
        global_df, summary = calculate_global_balance(monthly_input)
        return {
            "raw": monthly_input,
            "leaching": leaching_df,
            "sx": sx_df,
            "ew": ew_df,
            "global": global_df,
            "summary": summary,
        }

    def build_excel_bytes(self, period: Optional[str] = None) -> bytes:
        bundle = self.get_reports_bundle(period)
        return build_excel_report(bundle["raw"], bundle["leaching"], bundle["sx"], bundle["ew"], bundle["global"])

    def build_pdf_bytes(self, period: Optional[str] = None) -> bytes:
        bundle = self.get_reports_bundle(period)
        return build_pdf_report(bundle["summary"], bundle["global"])


@lru_cache(maxsize=1)
def get_service() -> BalanceService:
    return BalanceService()
