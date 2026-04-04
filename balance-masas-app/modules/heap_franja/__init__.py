"""Motor de balance por franja horizontal."""

from modules.heap_franja.aggregation import aggregate_cycle_results, aggregate_pad_results
from modules.heap_franja.acid_balance import calculate_acid_balance
from modules.heap_franja.copper_balance import calculate_copper_balance
from modules.heap_franja.dashboard_compare import build_compare_payload
from modules.heap_franja.dashboard_franja import build_franja_dashboard_payload
from modules.heap_franja.dashboard_pad import build_pad_dashboard_payload
from modules.heap_franja.gangue_proxies import calculate_drx_fe_factor, calculate_gangue_proxies
from modules.heap_franja.holdup import build_holdup_profile, calculate_design_holdup_volume
from modules.heap_franja.irrigation import (
    build_irrigation_timeline,
    build_routing_transitions,
    summarize_irrigation_sources,
)
from modules.heap_franja.kinetics import build_recovery_vs_rl_curve, project_cutoff_day
from modules.heap_franja.leach_ratio import calculate_leach_ratio, calculate_module_metrics
from modules.heap_franja.lifecycle import build_lifecycle_frame, infer_franja_state
from modules.heap_franja.models import (
    AcidBalanceSummary,
    Ciclo,
    CopperBalanceSummary,
    DatosPLSFranja,
    DatosRiegoModulo,
    EntradaPonderada,
    Franja,
    HeapFranjaDataset,
    LeachRatioSummary,
    Modulo,
    ModuleIrrigationMetric,
    Pad,
    RuteoModulo,
)
from modules.heap_franja.reconciliation import build_reconciliation_summary
from modules.heap_franja.routing_graph import build_cycle_routing_sankey
from modules.heap_franja.validators import build_cycle_alerts, build_franja_alerts
from modules.heap_franja.weighted_input import (
    build_weighted_input_for_franja,
    calculate_source_input_masses,
    calculate_weighted_input,
    calculate_weighted_input_for_day,
    classify_solution_phase,
)

__all__ = [
    "AcidBalanceSummary",
    "Ciclo",
    "CopperBalanceSummary",
    "DatosPLSFranja",
    "DatosRiegoModulo",
    "EntradaPonderada",
    "Franja",
    "HeapFranjaDataset",
    "LeachRatioSummary",
    "Modulo",
    "ModuleIrrigationMetric",
    "Pad",
    "RuteoModulo",
    "aggregate_cycle_results",
    "aggregate_pad_results",
    "build_compare_payload",
    "build_cycle_alerts",
    "build_cycle_routing_sankey",
    "build_franja_alerts",
    "build_franja_dashboard_payload",
    "build_holdup_profile",
    "build_irrigation_timeline",
    "build_lifecycle_frame",
    "build_pad_dashboard_payload",
    "build_reconciliation_summary",
    "build_recovery_vs_rl_curve",
    "build_routing_transitions",
    "build_weighted_input_for_franja",
    "calculate_acid_balance",
    "calculate_copper_balance",
    "calculate_design_holdup_volume",
    "calculate_drx_fe_factor",
    "calculate_gangue_proxies",
    "calculate_leach_ratio",
    "calculate_module_metrics",
    "calculate_source_input_masses",
    "calculate_weighted_input",
    "calculate_weighted_input_for_day",
    "classify_solution_phase",
    "infer_franja_state",
    "project_cutoff_day",
    "summarize_irrigation_sources",
]
