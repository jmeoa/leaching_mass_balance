"""
Generador de Base de Datos Sintética — Balance de Masas Lix/SX/EW

Genera datos realistas para:
- 1 pad dinámico
- 2 ciclos de operación
- 7 franjas por ciclo (6 operativas, 1 en preparación/desarme)
- 1 Mton por franja, 6 m altura
- Módulos de 1 hectárea (~10 módulos por franja)
- 120 días de riego por franja
- Muestreo diario

Parámetros calibrados con rangos típicos de operaciones de
lixiviación de cobre en el norte de Chile/sur de Perú.
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
from dataclasses import dataclass
import os
import json


# ============================================================
# PARÁMETROS DE DISEÑO
# ============================================================

@dataclass
class ParametrosPad:
    """Parámetros geométricos y operacionales del pad."""
    
    # Pad
    id_pad: str = "PAD-01"
    nombre: str = "Pad Dinámico Principal"
    
    # Ciclos
    n_ciclos: int = 2
    dias_riego_por_franja: int = 120
    dias_entre_ciclos: int = 30          # desarme + preparación
    
    # Franjas
    n_franjas_total: int = 7
    n_franjas_operativas: int = 6        # 1 siempre en prep/desarme
    tonelaje_por_franja_t: float = 1_000_000  # 1 Mton
    altura_m: float = 6.0
    
    # Módulos
    area_modulo_m2: float = 10_000       # 1 hectárea
    
    # Derivados
    @property
    def densidad_aparente_t_m3(self) -> float:
        return 1.6  # t/m³ típico mineral chancado
    
    @property
    def volumen_franja_m3(self) -> float:
        return self.tonelaje_por_franja_t / self.densidad_aparente_t_m3
    
    @property
    def area_franja_m2(self) -> float:
        return self.volumen_franja_m3 / self.altura_m
    
    @property
    def n_modulos_por_franja(self) -> int:
        return round(self.area_franja_m2 / self.area_modulo_m2)
    
    @property
    def area_total_pad_m2(self) -> float:
        return self.area_franja_m2 * self.n_franjas_total


# ============================================================
# PARÁMETROS MINERALÓGICOS Y METALÚRGICOS
# ============================================================

@dataclass
class PerfilMineral:
    """Perfil mineralógico y de leyes para una franja."""
    ley_cu_total_pct: float
    ley_cu_soluble_pct: float
    pct_goethita: float
    pct_jarosita: float
    pct_clorita: float
    pct_atacamita: float
    pct_crisocola: float
    pct_cuarzo: float
    pct_feldespatos: float
    pct_arcillas: float
    pct_mn_oxidos: float
    rec_max_esperada: float              # recuperación asintótica esperada (%)
    k_cinetica: float                    # constante cinética (1/día)
    consumo_ganga_inicial: float         # kg H₂SO₄/t mineral/día (día 1)
    tau_ganga: float                     # constante tiempo decaimiento ganga (días)


def generar_perfiles_minerales(n_franjas: int, seed: int = 42) -> list[PerfilMineral]:
    """
    Genera perfiles mineralógicos variados pero realistas.
    Simula variabilidad natural del yacimiento.
    """
    rng = np.random.default_rng(seed)
    
    perfiles = []
    for i in range(n_franjas):
        # Leyes Cu con variabilidad moderada
        ley_total = rng.uniform(0.35, 0.85)
        ratio_soluble = rng.uniform(0.55, 0.80)
        ley_soluble = ley_total * ratio_soluble
        
        # Mineralogía — debe sumar ~100% (con "otros" implícito)
        goethita = rng.uniform(3, 12)
        jarosita = rng.uniform(0.5, 4)
        clorita = rng.uniform(2, 8)
        atacamita = rng.uniform(0.5, 5)
        crisocola = rng.uniform(2, 10)
        cuarzo = rng.uniform(25, 45)
        feldespatos = rng.uniform(10, 25)
        arcillas = rng.uniform(5, 15)
        mn_oxidos = rng.uniform(0.2, 2.0)
        
        # Normalizar para que sume ~85-95% (resto = otros)
        total = goethita + jarosita + clorita + atacamita + crisocola + cuarzo + feldespatos + arcillas + mn_oxidos
        factor = rng.uniform(85, 95) / total
        
        # Cinética — correlacionada con mineralogía
        # Más atacamita/crisocola → más rápida la extracción
        ratio_reactivo = (atacamita + crisocola) / (atacamita + crisocola + goethita + clorita)
        rec_max = rng.uniform(55, 78)
        k = rng.uniform(0.015, 0.035) * (0.8 + 0.4 * ratio_reactivo)
        
        # Consumo de ganga — correlacionado con goethita + clorita + arcillas
        ganga_reactiva = goethita + clorita + arcillas
        consumo_ganga_ini = rng.uniform(0.8, 2.5) * (ganga_reactiva / 30)
        tau = rng.uniform(20, 50)
        
        perfiles.append(PerfilMineral(
            ley_cu_total_pct=round(ley_total, 3),
            ley_cu_soluble_pct=round(ley_soluble, 3),
            pct_goethita=round(goethita * factor, 2),
            pct_jarosita=round(jarosita * factor, 2),
            pct_clorita=round(clorita * factor, 2),
            pct_atacamita=round(atacamita * factor, 2),
            pct_crisocola=round(crisocola * factor, 2),
            pct_cuarzo=round(cuarzo * factor, 2),
            pct_feldespatos=round(feldespatos * factor, 2),
            pct_arcillas=round(arcillas * factor, 2),
            pct_mn_oxidos=round(mn_oxidos * factor, 2),
            rec_max_esperada=round(rec_max, 1),
            k_cinetica=round(k, 4),
            consumo_ganga_inicial=round(consumo_ganga_ini, 3),
            tau_ganga=round(tau, 1),
        ))
    
    return perfiles


# ============================================================
# GENERADOR DE DATOS DIARIOS
# ============================================================

def curva_extraccion(dia: int, rec_max: float, k: float) -> float:
    """Recuperación acumulada al día t: R(t) = R_max * (1 - exp(-k*t))"""
    return rec_max * (1 - np.exp(-k * dia))


def curva_consumo_ganga(dia: int, consumo_ini: float, tau: float) -> float:
    """Consumo de ácido por ganga: decae exponencialmente + residual."""
    residual = consumo_ini * 0.15  # 15% del inicial se mantiene
    return consumo_ini * np.exp(-dia / tau) + residual


def generar_datos_franja(
    id_franja: str,
    perfil: PerfilMineral,
    params: ParametrosPad,
    fecha_inicio: date,
    n_modulos: int,
    ruteo_config: dict,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Genera datos diarios de riego por módulo y PLS por franja.
    
    Usa un enfoque basado en CONCENTRACIONES PLS directas (no en masa)
    para garantizar valores realistas. Las concentraciones PLS se generan
    con curvas de decaimiento calibradas a operaciones reales.
    
    Returns:
        (df_riego_modulos, df_pls_franja)
    """
    dias = params.dias_riego_por_franja
    
    # ── Parámetros de concentración PLS ──
    # Cu PLS: pico inicial + decaimiento exponencial
    cu_pls_peak = rng.uniform(3.0, 5.5)       # g/L día ~5-10
    cu_pls_final = rng.uniform(0.4, 1.0)       # g/L día 120
    cu_pls_ramp_days = rng.integers(3, 8)      # días de rampa inicial
    
    # Ácido: el refino entra ~10 g/L, PLS sale ~3-6 g/L (consumo por mineral)
    acid_drop_inicial = rng.uniform(5, 8)       # g/L de caída (consumo alto al inicio)
    acid_drop_final = rng.uniform(2, 4)         # g/L de caída (estabilizado)
    
    # Fe PLS: sube respecto al refino por disolución de ganga
    fe_delta_peak = rng.uniform(1.5, 4.0)       # g/L incremento sobre refino
    fe_delta_final = rng.uniform(0.3, 1.0)      # g/L incremento estabilizado
    
    # Tasa de riego base (L/h/m²)
    tasa_riego_base = rng.uniform(7, 11)
    
    # Concentraciones de refino (desde SX, estables)
    cu_refino_base = rng.uniform(0.25, 0.45)
    acid_refino_base = rng.uniform(8, 14)
    fe_refino_base = rng.uniform(0.8, 1.8)
    fe2_refino_ratio = rng.uniform(0.3, 0.5)
    cl_refino_base = rng.uniform(0.1, 0.5)
    sio2_refino_base = rng.uniform(0.05, 0.2)
    mn_refino_base = rng.uniform(0.02, 0.1)
    
    registros_riego = []
    registros_pls = []
    
    for dia in range(dias):
        fecha = fecha_inicio + timedelta(days=dia)
        t = dia + 1  # día 1-based para curvas
        
        # ── Concentración entrada ponderada (para calcular después) ──
        vol_total_entrada = 0
        sum_cu_vol = 0    # Σ(vol × [Cu]) para ponderar
        sum_acid_vol = 0
        sum_fe_vol = 0
        sum_fe2_vol = 0
        sum_cl_vol = 0
        sum_sio2_vol = 0
        sum_mn_vol = 0
        
        for m in range(n_modulos):
            id_modulo = f"{id_franja}-M{m+1:02d}"
            
            # Ruteo
            ruteo = ruteo_config.get(id_modulo, {})
            tipo_sol = ruteo.get("tipo", "refino")
            fuente_ils = ruteo.get("fuente", None)
            if "cambio_dia" in ruteo and dia >= ruteo["cambio_dia"]:
                tipo_sol = ruteo.get("tipo_post", tipo_sol)
                fuente_ils = ruteo.get("fuente_post", fuente_ils)
            
            # Volumen de riego por módulo (m³/día)
            tasa = tasa_riego_base * rng.uniform(0.90, 1.10)
            vol_mod = tasa * params.area_modulo_m2 * 24 / 1000
            
            # Concentraciones según tipo de solución
            if tipo_sol == "refino":
                cu_ent = cu_refino_base * rng.uniform(0.95, 1.05)
                acid_ent = acid_refino_base * rng.uniform(0.95, 1.05)
                fe_ent = fe_refino_base * rng.uniform(0.90, 1.10)
                fe2_ent = fe_ent * fe2_refino_ratio * rng.uniform(0.90, 1.10)
                cl_ent = cl_refino_base * rng.uniform(0.90, 1.10)
                sio2_ent = sio2_refino_base * rng.uniform(0.90, 1.10)
                mn_ent = mn_refino_base * rng.uniform(0.90, 1.10)
            else:
                # ILS: más Cu, menos ácido que refino
                cu_ent = rng.uniform(1.0, 3.5)
                acid_ent = rng.uniform(4, 9)
                fe_ent = rng.uniform(1.5, 4.0)
                fe2_ent = fe_ent * rng.uniform(0.3, 0.6)
                cl_ent = rng.uniform(0.3, 1.2)
                sio2_ent = rng.uniform(0.1, 0.5)
                mn_ent = rng.uniform(0.05, 0.3)
            
            vol_total_entrada += vol_mod
            sum_cu_vol += vol_mod * cu_ent
            sum_acid_vol += vol_mod * acid_ent
            sum_fe_vol += vol_mod * fe_ent
            sum_fe2_vol += vol_mod * fe2_ent
            sum_cl_vol += vol_mod * cl_ent
            sum_sio2_vol += vol_mod * sio2_ent
            sum_mn_vol += vol_mod * mn_ent
            
            registros_riego.append({
                "id_modulo": id_modulo,
                "id_franja": id_franja,
                "fecha": fecha,
                "tipo_solucion": tipo_sol,
                "fuente_ils": fuente_ils,
                "vol_aplicado_m3": round(vol_mod, 1),
                "tasa_riego_lhm2": round(tasa, 2),
                "cu_entrada_gpl": round(cu_ent, 3),
                "acid_entrada_gpl": round(acid_ent, 2),
                "fe_total_entrada_gpl": round(fe_ent, 3),
                "fe2_entrada_gpl": round(fe2_ent, 3),
                "cl_entrada_gpl": round(cl_ent, 3),
                "sio2_entrada_gpl": round(sio2_ent, 3),
                "mn_entrada_gpl": round(mn_ent, 3),
            })
        
        # ── Concentraciones ponderadas de entrada ──
        cu_entrada_pond = sum_cu_vol / vol_total_entrada
        acid_entrada_pond = sum_acid_vol / vol_total_entrada
        fe_entrada_pond = sum_fe_vol / vol_total_entrada
        cl_entrada_pond = sum_cl_vol / vol_total_entrada
        sio2_entrada_pond = sum_sio2_vol / vol_total_entrada
        mn_entrada_pond = sum_mn_vol / vol_total_entrada
        
        # ── PLS de la franja — concentraciones directas ──
        
        # Volumen PLS (retención 3-8%)
        factor_retencion = rng.uniform(0.03, 0.08)
        vol_pls = vol_total_entrada * (1 - factor_retencion) * rng.uniform(0.97, 1.03)
        
        # [Cu] PLS: rampa inicial + decaimiento
        if t <= cu_pls_ramp_days:
            # Rampa de subida (primeros días, wetting up)
            cu_pls = cu_entrada_pond + (cu_pls_peak - cu_entrada_pond) * (t / cu_pls_ramp_days)
        else:
            # Decaimiento exponencial desde peak hacia final
            t_eff = t - cu_pls_ramp_days
            t_total = dias - cu_pls_ramp_days
            cu_pls = cu_pls_final + (cu_pls_peak - cu_pls_final) * np.exp(-2.5 * t_eff / t_total)
        cu_pls = cu_pls * rng.uniform(0.93, 1.07)  # ruido analítico
        cu_pls = max(cu_pls, cu_entrada_pond + 0.05)  # siempre > entrada
        
        # [H₂SO₄] PLS: entrada - consumo (alto al inicio, baja después)
        acid_drop = acid_drop_final + (acid_drop_inicial - acid_drop_final) * np.exp(-t / 30)
        acid_pls = acid_entrada_pond - acid_drop * rng.uniform(0.9, 1.1)
        acid_pls = max(acid_pls, 1.0)  # mínimo 1 g/L ácido libre
        
        # [Fe] PLS: entrada + incremento por disolución de ganga
        fe_delta = fe_delta_final + (fe_delta_peak - fe_delta_final) * np.exp(-t / 35)
        fe_pls = fe_entrada_pond + fe_delta * rng.uniform(0.85, 1.15)
        fe_pls = max(fe_pls, fe_entrada_pond)
        fe2_pls = fe_pls * rng.uniform(0.25, 0.50)
        
        # [Cl⁻] PLS: pico inicial fuerte (atacamita), decae rápido
        cl_peak_factor = perfil.pct_atacamita / 3
        cl_delta = cl_peak_factor * np.exp(-t / 12) * rng.uniform(0.8, 1.2)
        cl_pls = cl_entrada_pond + cl_delta
        
        # [SiO₂] PLS: incremento lento, relativamente estable
        sio2_delta = rng.uniform(0.05, 0.20) * (perfil.pct_crisocola + perfil.pct_arcillas) / 15
        sio2_pls = sio2_entrada_pond + sio2_delta * rng.uniform(0.85, 1.15)
        
        # [Mn] PLS: incremento moderado, decae gradualmente
        mn_delta = rng.uniform(0.03, 0.15) * perfil.pct_mn_oxidos * np.exp(-t / 50)
        mn_pls = mn_entrada_pond + mn_delta * rng.uniform(0.8, 1.2)
        
        registros_pls.append({
            "id_franja": id_franja,
            "fecha": fecha,
            "vol_pls_m3": round(vol_pls, 1),
            "cu_pls_gpl": round(cu_pls, 3),
            "acid_pls_gpl": round(acid_pls, 2),
            "fe_total_pls_gpl": round(fe_pls, 3),
            "fe2_pls_gpl": round(fe2_pls, 3),
            "cl_pls_gpl": round(cl_pls, 3),
            "sio2_pls_gpl": round(sio2_pls, 3),
            "mn_pls_gpl": round(mn_pls, 3),
        })
    
    return pd.DataFrame(registros_riego), pd.DataFrame(registros_pls)


# ============================================================
# GENERADOR DE RUTEO
# ============================================================

def generar_ruteo_ciclo(
    id_ciclo: str,
    franjas_ids: list[str],
    n_modulos: int,
    rng: np.random.Generator,
) -> dict:
    """
    Genera configuración de ruteo realista para un ciclo.
    
    Lógica típica:
    - Franjas frescas (primeros 30 días): 100% refino
    - Franjas intermedias: mix refino + ILS
    - Franjas maduras: predomina ILS
    - ILS proviene de franjas frescas (mayor ácido residual en su PLS)
    """
    ruteo = {}
    n_franjas = len(franjas_ids)
    
    for f_idx, id_franja in enumerate(franjas_ids):
        for m in range(n_modulos):
            id_modulo = f"{id_franja}-M{m+1:02d}"
            
            if f_idx < 2:
                # Franjas 1-2 (más frescas): mayormente refino
                if m < n_modulos - 2:
                    ruteo[id_modulo] = {"tipo": "refino"}
                else:
                    # Últimos 2 módulos cambian a ILS a los 40 días
                    fuente = franjas_ids[min(f_idx + 3, n_franjas - 1)]
                    ruteo[id_modulo] = {
                        "tipo": "refino",
                        "cambio_dia": 40,
                        "tipo_post": "ils",
                        "fuente": None,
                        "fuente_post": fuente,
                    }
            elif f_idx < 4:
                # Franjas 3-4 (intermedias): mix desde el inicio
                if m % 3 == 0:
                    ruteo[id_modulo] = {"tipo": "refino"}
                else:
                    fuente = franjas_ids[rng.choice([0, 1])]
                    ruteo[id_modulo] = {
                        "tipo": "refino",
                        "cambio_dia": 20,
                        "tipo_post": "ils",
                        "fuente": None,
                        "fuente_post": fuente,
                    }
            else:
                # Franjas 5-6 (maduras): predomina ILS
                if m == 0:
                    ruteo[id_modulo] = {"tipo": "refino"}  # 1 módulo con refino
                else:
                    fuente = franjas_ids[rng.choice(range(min(3, n_franjas)))]
                    ruteo[id_modulo] = {
                        "tipo": "refino",
                        "cambio_dia": 10,
                        "tipo_post": "ils",
                        "fuente": None,
                        "fuente_post": fuente,
                    }
    
    return ruteo


# ============================================================
# GENERADOR PRINCIPAL
# ============================================================

def generar_database(output_dir: str = "data/synthetic", seed: int = 42):
    """Genera la base de datos sintética completa."""
    
    rng = np.random.default_rng(seed)
    params = ParametrosPad()
    
    print("=" * 60)
    print("  GENERADOR DE BASE DE DATOS SINTÉTICA")
    print("  Balance de Masas Cu/H₂SO₄ — Lix/SX/EW")
    print("=" * 60)
    print(f"\n  Pad: {params.id_pad}")
    print(f"  Ciclos: {params.n_ciclos}")
    print(f"  Franjas por ciclo: {params.n_franjas_total} ({params.n_franjas_operativas} operativas)")
    print(f"  Tonelaje por franja: {params.tonelaje_por_franja_t:,.0f} t")
    print(f"  Altura: {params.altura_m} m")
    print(f"  Área por franja: {params.area_franja_m2:,.0f} m² ({params.area_franja_m2/10000:.1f} ha)")
    print(f"  Módulos por franja: {params.n_modulos_por_franja} ({params.area_modulo_m2/10000:.0f} ha c/u)")
    print(f"  Días de riego: {params.dias_riego_por_franja}")
    print(f"  Área total pad: {params.area_total_pad_m2:,.0f} m² ({params.area_total_pad_m2/10000:.1f} ha)")
    print()
    
    os.makedirs(output_dir, exist_ok=True)
    
    n_modulos = params.n_modulos_por_franja
    
    # ── 1. Tabla de Pad ──
    df_pad = pd.DataFrame([{
        "id_pad": params.id_pad,
        "nombre": params.nombre,
        "area_total_m2": round(params.area_total_pad_m2, 0),
        "capacidad_max_franjas": params.n_franjas_total,
    }])
    
    # ── 2. Generar ciclos ──
    registros_ciclos = []
    registros_franjas = []
    registros_modulos = []
    registros_ruteo = []
    all_riego = []
    all_pls = []
    
    fecha_cursor = date(2024, 1, 15)  # inicio del primer ciclo
    
    for ciclo_num in range(1, params.n_ciclos + 1):
        id_ciclo = f"{params.id_pad}-C{ciclo_num:02d}"
        fecha_inicio_ciclo = fecha_cursor
        
        # Generar perfiles mineralógicos variados para este ciclo
        perfiles = generar_perfiles_minerales(
            params.n_franjas_total,
            seed=seed + ciclo_num * 100
        )
        
        # Franjas del ciclo (7 total, 6 operativas)
        franjas_ids = []
        franja_inactiva = rng.integers(0, params.n_franjas_total)  # 1 franja en prep
        
        for f_num in range(1, params.n_franjas_total + 1):
            id_franja = f"{id_ciclo}-F{f_num:02d}"
            franjas_ids.append(id_franja)
            
            perfil = perfiles[f_num - 1]
            operativa = (f_num - 1) != franja_inactiva
            
            # Fechas: las franjas arrancan escalonadas (cada 5-15 días)
            if operativa:
                offset_dias = int((f_num - 1) * rng.integers(5, 15))
                fecha_on = fecha_inicio_ciclo + timedelta(days=offset_dias)
                fecha_off = fecha_on + timedelta(days=params.dias_riego_por_franja)
            else:
                fecha_on = None
                fecha_off = None
            
            # Ley residual (solo para franjas completadas)
            ley_residual = None
            if operativa and ciclo_num == 1:
                rec_final = curva_extraccion(
                    params.dias_riego_por_franja,
                    perfil.rec_max_esperada,
                    perfil.k_cinetica
                )
                ley_residual = round(
                    perfil.ley_cu_soluble_pct * (1 - rec_final / 100), 4
                )
            
            registros_franjas.append({
                "id_franja": id_franja,
                "id_ciclo": id_ciclo,
                "numero_franja": f_num,
                "n_modulos": n_modulos,
                "operativa": operativa,
                "fecha_on": fecha_on,
                "fecha_off": fecha_off,
                "tonelaje_t": params.tonelaje_por_franja_t,
                "area_m2": round(params.area_franja_m2, 0),
                "altura_m": params.altura_m,
                "ley_cu_total_pct": perfil.ley_cu_total_pct,
                "ley_cu_soluble_pct": perfil.ley_cu_soluble_pct,
                "ley_cu_residual_pct": ley_residual,
                "humedad_residual_pct": round(rng.uniform(8, 12), 1),
                "pct_goethita": perfil.pct_goethita,
                "pct_jarosita": perfil.pct_jarosita,
                "pct_clorita": perfil.pct_clorita,
                "pct_atacamita": perfil.pct_atacamita,
                "pct_crisocola": perfil.pct_crisocola,
                "pct_cuarzo": perfil.pct_cuarzo,
                "pct_feldespatos": perfil.pct_feldespatos,
                "pct_arcillas": perfil.pct_arcillas,
                "pct_mn_oxidos": perfil.pct_mn_oxidos,
            })
            
            # Módulos de la franja
            for m_num in range(1, n_modulos + 1):
                id_modulo = f"{id_franja}-M{m_num:02d}"
                # Área: último módulo puede ser más chico si no calza exacto
                area_mod = params.area_modulo_m2
                if m_num == n_modulos:
                    area_restante = params.area_franja_m2 - (n_modulos - 1) * params.area_modulo_m2
                    area_mod = max(area_restante, params.area_modulo_m2 * 0.5)
                
                registros_modulos.append({
                    "id_modulo": id_modulo,
                    "id_franja": id_franja,
                    "numero_modulo": m_num,
                    "area_m2": round(area_mod, 0),
                    "tonelaje_estimado_t": round(
                        params.tonelaje_por_franja_t * area_mod / params.area_franja_m2, 0
                    ),
                })
        
        # Franjas operativas para generar datos
        franjas_operativas = [
            (f, p) for f, p, r in zip(
                registros_franjas[-params.n_franjas_total:],
                perfiles,
                range(params.n_franjas_total)
            )
            if f["operativa"]
        ]
        
        franjas_op_ids = [f["id_franja"] for f, _ in franjas_operativas]
        
        # Generar ruteo
        ruteo_ciclo = generar_ruteo_ciclo(id_ciclo, franjas_op_ids, n_modulos, rng)
        
        # Guardar ruteo como registros
        for id_mod, config in ruteo_ciclo.items():
            id_franja_mod = "-".join(id_mod.split("-")[:-1])
            franja_data = next(
                (f for f in registros_franjas if f["id_franja"] == id_franja_mod), None
            )
            if franja_data and franja_data["fecha_on"]:
                registros_ruteo.append({
                    "id_modulo": id_mod,
                    "fecha_inicio": franja_data["fecha_on"],
                    "fecha_fin": (
                        franja_data["fecha_on"] + timedelta(days=config.get("cambio_dia", params.dias_riego_por_franja))
                        if "cambio_dia" in config else franja_data["fecha_off"]
                    ),
                    "tipo_solucion": config["tipo"],
                    "fuente_ils": config.get("fuente", None),
                    "notas": "Asignación inicial",
                })
                if "cambio_dia" in config:
                    registros_ruteo.append({
                        "id_modulo": id_mod,
                        "fecha_inicio": franja_data["fecha_on"] + timedelta(days=config["cambio_dia"]),
                        "fecha_fin": franja_data["fecha_off"],
                        "tipo_solucion": config.get("tipo_post", "ils"),
                        "fuente_ils": config.get("fuente_post", None),
                        "notas": f"Cambio a ILS día {config['cambio_dia']}",
                    })
        
        # Generar datos diarios por franja operativa
        print(f"  Generando Ciclo {ciclo_num}...")
        for franja_data, perfil in franjas_operativas:
            id_franja = franja_data["id_franja"]
            print(f"    → {id_franja} (ley CuS: {perfil.ley_cu_soluble_pct:.3f}%, "
                  f"Rec_max: {perfil.rec_max_esperada:.1f}%)")
            
            df_riego, df_pls = generar_datos_franja(
                id_franja=id_franja,
                perfil=perfil,
                params=params,
                fecha_inicio=franja_data["fecha_on"],
                n_modulos=n_modulos,
                ruteo_config=ruteo_ciclo,
                rng=rng,
            )
            all_riego.append(df_riego)
            all_pls.append(df_pls)
        
        # Fecha fin del ciclo
        fechas_off = [
            f["fecha_off"] for f in registros_franjas[-params.n_franjas_total:]
            if f["fecha_off"]
        ]
        fecha_fin_ciclo = max(fechas_off) if fechas_off else None
        
        registros_ciclos.append({
            "id_ciclo": id_ciclo,
            "id_pad": params.id_pad,
            "numero_ciclo": ciclo_num,
            "n_franjas": params.n_franjas_total,
            "n_franjas_operativas": params.n_franjas_operativas,
            "fecha_inicio": fecha_inicio_ciclo,
            "fecha_fin": fecha_fin_ciclo,
            "cut_off_acid_cu": round(rng.uniform(3.5, 5.5), 1),
            "estado": "cerrado" if ciclo_num == 1 else "activo",
        })
        
        # Avanzar cursor para siguiente ciclo
        if fecha_fin_ciclo:
            fecha_cursor = fecha_fin_ciclo + timedelta(days=params.dias_entre_ciclos)
    
    # ── Consolidar y guardar ──
    print(f"\n  Guardando en {output_dir}/...")
    
    df_ciclos = pd.DataFrame(registros_ciclos)
    df_franjas = pd.DataFrame(registros_franjas)
    df_modulos = pd.DataFrame(registros_modulos)
    df_ruteo = pd.DataFrame(registros_ruteo)
    df_riego_all = pd.concat(all_riego, ignore_index=True)
    df_pls_all = pd.concat(all_pls, ignore_index=True)
    
    # Guardar CSVs
    df_pad.to_csv(f"{output_dir}/pads.csv", index=False)
    df_ciclos.to_csv(f"{output_dir}/ciclos.csv", index=False)
    df_franjas.to_csv(f"{output_dir}/franjas.csv", index=False)
    df_modulos.to_csv(f"{output_dir}/modulos.csv", index=False)
    df_ruteo.to_csv(f"{output_dir}/ruteo.csv", index=False)
    df_riego_all.to_csv(f"{output_dir}/riego_diario.csv", index=False)
    df_pls_all.to_csv(f"{output_dir}/pls_diario.csv", index=False)
    
    # Guardar también como Excel (un archivo con todas las hojas)
    with pd.ExcelWriter(f"{output_dir}/database_sintetica.xlsx", engine="openpyxl") as writer:
        df_pad.to_excel(writer, sheet_name="pads", index=False)
        df_ciclos.to_excel(writer, sheet_name="ciclos", index=False)
        df_franjas.to_excel(writer, sheet_name="franjas", index=False)
        df_modulos.to_excel(writer, sheet_name="modulos", index=False)
        df_ruteo.to_excel(writer, sheet_name="ruteo", index=False)
        # Riego y PLS son muy grandes, sample para Excel
        df_riego_sample = df_riego_all.head(5000)
        df_pls_sample = df_pls_all.head(5000)
        df_riego_sample.to_excel(writer, sheet_name="riego_diario_sample", index=False)
        df_pls_sample.to_excel(writer, sheet_name="pls_diario_sample", index=False)
    
    # Resumen
    print(f"\n  {'─' * 50}")
    print(f"  RESUMEN DE LA BASE DE DATOS GENERADA")
    print(f"  {'─' * 50}")
    print(f"  Pads:                {len(df_pad)}")
    print(f"  Ciclos:              {len(df_ciclos)}")
    print(f"  Franjas:             {len(df_franjas)} ({df_franjas['operativa'].sum()} operativas)")
    print(f"  Módulos:             {len(df_modulos)}")
    print(f"  Registros ruteo:     {len(df_ruteo)}")
    print(f"  Registros riego:     {len(df_riego_all):,}")
    print(f"  Registros PLS:       {len(df_pls_all):,}")
    print(f"  Rango de fechas:     {df_pls_all['fecha'].min()} a {df_pls_all['fecha'].max()}")
    print(f"  {'─' * 50}")
    
    # Estadísticas de leyes
    print(f"\n  ESTADÍSTICAS DE LEYES (franjas operativas)")
    franjas_op = df_franjas[df_franjas["operativa"]]
    print(f"  Ley Cu total:    {franjas_op['ley_cu_total_pct'].mean():.3f}% "
          f"(min {franjas_op['ley_cu_total_pct'].min():.3f}, max {franjas_op['ley_cu_total_pct'].max():.3f})")
    print(f"  Ley Cu soluble:  {franjas_op['ley_cu_soluble_pct'].mean():.3f}% "
          f"(min {franjas_op['ley_cu_soluble_pct'].min():.3f}, max {franjas_op['ley_cu_soluble_pct'].max():.3f})")
    
    # Estadísticas de PLS
    print(f"\n  ESTADÍSTICAS DE PLS")
    print(f"  [Cu] PLS:   {df_pls_all['cu_pls_gpl'].mean():.2f} g/L "
          f"(min {df_pls_all['cu_pls_gpl'].min():.2f}, max {df_pls_all['cu_pls_gpl'].max():.2f})")
    print(f"  [Acid] PLS: {df_pls_all['acid_pls_gpl'].mean():.2f} g/L "
          f"(min {df_pls_all['acid_pls_gpl'].min():.2f}, max {df_pls_all['acid_pls_gpl'].max():.2f})")
    print(f"  [Fe] PLS:   {df_pls_all['fe_total_pls_gpl'].mean():.2f} g/L")
    
    # Guardar metadata
    metadata = {
        "generado": str(date.today()),
        "seed": seed,
        "parametros": {
            "n_ciclos": params.n_ciclos,
            "n_franjas_total": params.n_franjas_total,
            "n_franjas_operativas": params.n_franjas_operativas,
            "tonelaje_por_franja_t": params.tonelaje_por_franja_t,
            "altura_m": params.altura_m,
            "area_modulo_m2": params.area_modulo_m2,
            "n_modulos_por_franja": params.n_modulos_por_franja,
            "area_franja_m2": round(params.area_franja_m2, 0),
            "dias_riego": params.dias_riego_por_franja,
        },
        "archivos": {
            "pads.csv": len(df_pad),
            "ciclos.csv": len(df_ciclos),
            "franjas.csv": len(df_franjas),
            "modulos.csv": len(df_modulos),
            "ruteo.csv": len(df_ruteo),
            "riego_diario.csv": len(df_riego_all),
            "pls_diario.csv": len(df_pls_all),
        },
    }
    with open(f"{output_dir}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    
    print(f"\n  ✓ Base de datos generada exitosamente en {output_dir}/")
    print(f"  ✓ Excel consolidado: {output_dir}/database_sintetica.xlsx")
    print(f"  ✓ Metadata: {output_dir}/metadata.json")
    
    return {
        "pad": df_pad,
        "ciclos": df_ciclos,
        "franjas": df_franjas,
        "modulos": df_modulos,
        "ruteo": df_ruteo,
        "riego_diario": df_riego_all,
        "pls_diario": df_pls_all,
    }


if __name__ == "__main__":
    generar_database()
