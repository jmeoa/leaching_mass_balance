"""Motor de balance por franja horizontal."""

from modules.heap_franja.acid_balance import calculate_acid_balance
from modules.heap_franja.copper_balance import calculate_copper_balance
from modules.heap_franja.gangue_proxies import calculate_drx_fe_factor, calculate_gangue_proxies
from modules.heap_franja.holdup import build_holdup_profile, calculate_design_holdup_volume
from modules.heap_franja.leach_ratio import calculate_leach_ratio, calculate_module_metrics
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
    "build_holdup_profile",
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
]
