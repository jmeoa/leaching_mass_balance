# Módulo: Balance de Soluciones — Pad Dinámico Horizontal

## 1. Objetivo

Calcular la recuperación de cobre y consumo de ácido sulfúrico por **franja horizontal** en pads dinámicos single-lift, con subdivisión en **módulos de riego** con ruteo configurable de soluciones (Refino / ILS), descomposición del ácido por componente, y análisis de razón de lixiviación.

---

## 2. Geometría del Pad

```
PAD DINÁMICO — VISTA PLANTA
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  ┌────────┬────────┬────────┐   FRANJA 1 (fresca)       │
│  │  M1.1  │  M1.2  │  M1.3  │   3 módulos               │
│  │ refino │ refino │  ILS   │   ← tipo riego por módulo  │
│  └────────┴────────┴────────┘                            │
│                                                          │
│  ┌────────┬────────┬────────┐   FRANJA 2 (intermedia)    │
│  │  M2.1  │  M2.2  │  M2.3  │   3 módulos               │
│  │  ILS   │  ILS   │ refino │                            │
│  └────────┴────────┴────────┘                            │
│                                                          │
│  ┌──────────┬──────────┐        FRANJA 3 (madura)        │
│  │   M3.1   │   M3.2   │        2 módulos                │
│  │   ILS    │   ILS    │        ← todo ILS (casi OFF)    │
│  └──────────┴──────────┘                                 │
│                                                          │
│  ═══════════════════════════  Colector PLS por franja     │
│  PLS F1        PLS F2        PLS F3                      │
│  (muestreo)   (muestreo)   (muestreo)                   │
└──────────────────────────────────────────────────────────┘
```

### Principios

- Las **franjas** están en el mismo plano horizontal, NO apiladas
- Cada franja es **single-lift** (una sola capa de mineral)
- Cada franja se subdivide en **N módulos** (definido por el usuario)
- El **tipo de solución** (refino o ILS) se asigna **por módulo**
- El **PLS se colecta por franja** (todos los módulos de una franja drenan juntos)
- El **muestreo** (Cu, ácido, Fe, Cl⁻, SiO₂, Mn) es **a nivel de franja**
- El **balance de masas** se cierra **a nivel de franja**
- Los **módulos** son unidades de **gestión de riego**, no de balance

---

## 3. Ruteo de Soluciones

### 3.1 Concepto

El usuario define libremente qué solución recibe cada módulo y de dónde viene el ILS.

```
EJEMPLO DE RUTEO CONFIGURABLE:

  Refino (SX) ──┬──▶ M1.1, M1.2 (franja fresca, riego directo)
                │
                └──▶ M2.3 (módulo específico de F2 recibe refino fresco)

  PLS F1 ──────────▶ no se usa como ILS (va directo a SX, alta ley)

  PLS F2 ────┬─────▶ M3.1, M3.2 (franja madura recibe ILS de F2)
             │
             └─────▶ M1.3 (un módulo de F1 recibe ILS de F2)

  PLS F3 ──────────▶ descarte o recirculación (baja ley)
```

### 3.2 Modelo de Ruteo

```python
@dataclass
class RuteoModulo:
    """Define qué solución recibe un módulo en un período dado."""
    id_modulo: str
    fecha_inicio: date
    fecha_fin: date | None        # None = vigente
    tipo_solucion: str            # "refino" | "ils"
    fuente_ils: str | None        # id_franja origen del ILS (None si refino)
    proporcion_flujo: float       # Fracción del flujo total que recibe (0-1)
    notas: str

# Ejemplo: M2.1 recibe ILS de Franja 3 desde marzo
RuteoModulo(
    id_modulo="PAD01-C01-F2-M1",
    fecha_inicio=date(2025, 3, 1),
    tipo_solucion="ils",
    fuente_ils="PAD01-C01-F3",
    proporcion_flujo=0.5,         # recibe 50% del PLS de F3
    notas="Cambio a ILS por baja ley F3"
)
```

### 3.3 Cambios de Ruteo en el Tiempo

```
TIMELINE DE RUTEO — Módulo M2.1
─────────────────────────────────────────────
Ene    Feb    Mar    Abr    May    Jun
█████ REFINO █████│▓▓▓▓▓ ILS(F3) ▓▓▓▓▓│░░ ILS(F1) ░░│
                  ↑                     ↑
                  Cambio 1              Cambio 2

Cada cambio de ruteo genera un registro en la tabla de transiciones.
El sistema trackea automáticamente cuántos días y cuánto volumen
recibió cada módulo de cada tipo/fuente.
```

---

## 4. Modelo de Datos

### 4.1 Pad

```
PAD
├── id_pad                : str
├── nombre                : str
├── area_total_m2         : float
└── estado                : str       — "activo" | "mantenimiento"
```

### 4.2 Ciclo

```
CICLO
├── id_ciclo              : str       — "PAD01-C03"
├── id_pad                : str
├── numero_ciclo          : int
├── n_franjas             : int       — Definido por usuario
├── fecha_inicio          : date
├── fecha_fin             : date|null
├── cut_off_acid_cu       : float     — Ratio ácido/Cu para OFF (kg/kg)
└── estado                : str       — "activo" | "cerrado"
```

### 4.3 Franja

```
FRANJA
├── id_franja             : str       — "PAD01-C03-F02"
├── id_ciclo              : str
├── numero_franja         : int
├── n_modulos             : int       — Definido por usuario para esta franja
├── fecha_on              : date
├── fecha_off             : date|null
│
│ MINERAL
├── tonelaje_t            : float
├── ley_cu_total_pct      : float
├── ley_cu_soluble_pct    : float
├── ley_cu_residual_pct   : float     — Opcional, al OFF
├── humedad_residual_pct  : float     — Default 10%
├── area_franja_m2        : float
├── altura_m              : float
│
│ MINERALOGÍA (DRX/QEMSCAN)
├── pct_goethita          : float
├── pct_jarosita          : float
├── pct_clorita           : float
├── pct_atacamita         : float
├── pct_crisocola         : float
├── pct_cuarzo            : float
├── pct_feldespatos       : float
├── pct_arcillas          : float
├── pct_mn_oxidos         : float
└── otros_minerales       : dict
```

### 4.4 Módulo (unidad de riego)

```
MÓDULO
├── id_modulo             : str       — "PAD01-C03-F02-M01"
├── id_franja             : str
├── numero_modulo         : int
├── area_modulo_m2        : float     — Área de riego de este módulo
├── tonelaje_estimado_t   : float     — Prorrateo por área: franja.ton * (area_mod/area_franja)
└── estado                : str       — "regando" | "en_reposo" | "off"
```

### 4.5 Ruteo de Soluciones (por módulo, variable en el tiempo)

```
RUTEO
├── id_ruteo              : str       — Autoincremental
├── id_modulo             : str
├── fecha_inicio          : date
├── fecha_fin             : date|null — null = vigente
├── tipo_solucion         : str       — "refino" | "ils"
├── fuente_ils            : str|null  — id_franja origen (null si refino)
├── proporcion_flujo      : float     — Fracción del PLS fuente que recibe
└── notas                 : str
```

### 4.6 Datos Operacionales Diarios (por MÓDULO para riego, por FRANJA para PLS)

```
RIEGO_MODULO_DIARIO
├── id_modulo             : str
├── fecha                 : date
├── tipo_solucion         : str       — "refino" | "ils" (del ruteo vigente)
├── fuente_ils            : str|null
├── vol_aplicado_m3       : float     — Volumen regado en este módulo
├── tasa_riego_lhm2       : float     — Tasa de riego real
│
│ QUÍMICA DE ENTRADA (de la fuente: refino o PLS de franja origen)
├── cu_entrada_gpl        : float
├── acid_entrada_gpl      : float
├── fe_total_entrada_gpl  : float
├── fe2_entrada_gpl       : float
├── cl_entrada_gpl        : float
├── sio2_entrada_gpl      : float
└── mn_entrada_gpl        : float

PLS_FRANJA_DIARIO
├── id_franja             : str
├── fecha                 : date
│
│ PLS COLECTADO (mezcla de todos los módulos de la franja)
├── vol_pls_m3            : float
├── cu_pls_gpl            : float
├── acid_pls_gpl          : float
├── fe_total_pls_gpl      : float
├── fe2_pls_gpl           : float
├── cl_pls_gpl            : float
├── sio2_pls_gpl          : float
└── mn_pls_gpl            : float
```

---

## 5. Motor de Cálculo

### 5.1 Solución de Entrada Ponderada de la Franja

```python
# El PLS es por franja, pero la entrada varía por módulo.
# Para cerrar el balance necesitamos la ENTRADA TOTAL PONDERADA de la franja.

def entrada_ponderada_franja(franja, modulos_data, fecha):
    """
    Calcula el volumen y concentración de entrada total a la franja,
    ponderando por los módulos y sus distintas fuentes de solución.
    """
    vol_total = 0
    masa_cu = 0
    masa_acid = 0
    masa_fe = 0
    masa_cl = 0
    masa_sio2 = 0
    masa_mn = 0

    for mod in modulos_data:
        vol_total   += mod.vol_aplicado_m3
        masa_cu     += mod.vol_aplicado_m3 * mod.cu_entrada_gpl / 1000   # kg
        masa_acid   += mod.vol_aplicado_m3 * mod.acid_entrada_gpl / 1000
        masa_fe     += mod.vol_aplicado_m3 * mod.fe_total_entrada_gpl / 1000
        masa_cl     += mod.vol_aplicado_m3 * mod.cl_entrada_gpl / 1000
        masa_sio2   += mod.vol_aplicado_m3 * mod.sio2_entrada_gpl / 1000
        masa_mn     += mod.vol_aplicado_m3 * mod.mn_entrada_gpl / 1000

    return EntradaPonderada(
        vol_total_m3=vol_total,
        cu_ponderado_gpl=masa_cu * 1000 / vol_total if vol_total > 0 else 0,
        acid_ponderado_gpl=masa_acid * 1000 / vol_total if vol_total > 0 else 0,
        # ... idem para fe, cl, sio2, mn
        masa_cu_kg=masa_cu,
        masa_acid_kg=masa_acid,
        masa_fe_kg=masa_fe,
        masa_cl_kg=masa_cl,
        masa_sio2_kg=masa_sio2,
        masa_mn_kg=masa_mn,
        # Desglose por tipo de solución
        vol_refino_m3=sum(m.vol for m in modulos_data if m.tipo == "refino"),
        vol_ils_m3=sum(m.vol for m in modulos_data if m.tipo == "ils"),
        n_modulos_refino=count(m for m in modulos_data if m.tipo == "refino"),
        n_modulos_ils=count(m for m in modulos_data if m.tipo == "ils"),
    )
```

### 5.2 Balance de Cobre por Franja (directo)

```python
# ENTRADA: ponderada de todos los módulos
entrada = entrada_ponderada_franja(franja, modulos_data, fecha)

# SALIDA: PLS medido de la franja
pls = pls_franja_diario[fecha]

# Cu extraído en el día
cu_extraido_dia = (pls.vol_pls_m3 * pls.cu_pls_gpl - entrada.masa_cu_kg * 1000) / 1000
# Simplificado:
cu_extraido_dia = pls.masa_cu_kg - entrada.masa_cu_kg  # kg

# Acumulado + corrección holdup
cu_extraido_acum = Σ(cu_extraido_dia) + cu_holdup_inicio - cu_holdup_actual

# Recuperación directa
cu_contenido = franja.tonelaje_t * 1000 * franja.ley_cu_soluble_pct / 100
recuperacion_pct = cu_extraido_acum / cu_contenido * 100
```

### 5.3 Balance de Ácido por Franja (directo, descompuesto)

```python
# Consumo neto total
acid_consumido = entrada.masa_acid_kg - pls.masa_acid_kg

# Descomposición (misma lógica, ahora con entrada ponderada)
acid_por_cu   = cu_extraido_dia * 1.543
acid_por_fe   = fe_neto_disuelto * factor_drx_franja
acid_por_cl   = cl_neto_disuelto * 2.8
acid_por_sio2 = sio2_neto_disuelto * 1.63
acid_por_mn   = mn_neto_disuelto * 1.78
acid_no_asignado = acid_consumido - sum(acid_por_*)

# Ratio cut-off
ratio_acid_cu_acum = acid_consumido_acum / cu_extraido_acum
```

### 5.4 Razón de Lixiviación por Franja

```python
# RL total
rl_total = Σ(entrada.vol_total_m3) / franja.tonelaje_t  # m³/t

# RL segregada por tipo de solución
rl_refino = Σ(entrada.vol_refino_m3) / franja.tonelaje_t  # m³/t
rl_ils    = Σ(entrada.vol_ils_m3) / franja.tonelaje_t     # m³/t

# RL por fuente de ILS (detalle)
rl_por_fuente = {}
for fuente in fuentes_ils_unicas:
    vol = Σ(vol de módulos cuya fuente_ils == fuente)
    rl_por_fuente[fuente] = vol / franja.tonelaje_t

# RL normalizada
rl_por_area = Σ(vol_total) / franja.area_franja_m2       # m (columna equiv.)
rl_por_metro = rl_por_area / franja.altura_m              # volúmenes de poro

# Tasa de aplicación
tasa_global = Σ(vol_total) / franja.area_franja_m2 / dias  # m³/m²/día
```

### 5.5 Métricas de Riego por Módulo

```python
# Aunque el balance se cierra por franja, cada módulo tiene métricas de riego

for modulo in franja.modulos:
    # Volumen acumulado aplicado
    vol_acum = Σ(riego_diario.vol_aplicado_m3)

    # RL del módulo (estimada con tonelaje prorrateado por área)
    ton_mod = franja.tonelaje_t * modulo.area_m2 / franja.area_m2
    rl_modulo = vol_acum / ton_mod

    # Días por tipo de solución
    dias_refino = count(días con tipo="refino")
    dias_ils    = count(días con tipo="ils")
    dias_reposo = count(días sin riego)

    # Ácido aplicado por tipo
    acid_refino = Σ(vol * acid_gpl donde tipo="refino") / 1000
    acid_ils    = Σ(vol * acid_gpl donde tipo="ils") / 1000

    # Historial de fuentes ILS
    fuentes = distinct(fuente_ils por período)

    # Uniformidad de riego (comparación entre módulos de la franja)
    # rl_modulo vs rl_promedio_franja → detectar módulos sub/sobre regados
```

### 5.6 Eficiencia por Tipo de Solución (a nivel de franja)

```python
# Segregar la extracción de Cu según qué tipo de solución dominaba

# Períodos donde >70% del vol de entrada fue refino
dias_predomina_refino = [d for d in dias if entrada[d].vol_refino / entrada[d].vol_total > 0.7]
dias_predomina_ils    = [d for d in dias if entrada[d].vol_ils / entrada[d].vol_total > 0.7]
dias_mixto            = [d for d in dias if d not in dias_predomina_refino + dias_predomina_ils]

cu_fase_refino = Σ(cu_extraido_dia para dias_predomina_refino)
cu_fase_ils    = Σ(cu_extraido_dia para dias_predomina_ils)
cu_fase_mixto  = Σ(cu_extraido_dia para dias_mixto)

# Eficiencia volumétrica
efic_refino = cu_fase_refino / Σ(vol_total para dias_predomina_refino)  # kg Cu/m³
efic_ils    = cu_fase_ils / Σ(vol_total para dias_predomina_ils)        # kg Cu/m³
```

---

## 6. Interacciones entre Franjas vía ILS

### 6.1 Grafo de Ruteo

```python
# El ruteo de ILS crea un GRAFO DIRIGIDO entre franjas
# que el sistema debe trackear y visualizar

@dataclass
class GrafoRuteo:
    """Grafo de flujo de soluciones entre franjas."""

    nodos: list[str]      # id_franja
    aristas: list[dict]   # {origen, destino, vol_m3, [Cu]_gpl, tipo}

# Ejemplo en un momento dado:
#
#   REFINO ──▶ F1 (módulos M1.1, M1.2)
#              │
#   REFINO ──▶ F2 (módulo M2.3)
#              │
#   PLS F2 ──▶ F3 (módulos M3.1, M3.2) como ILS
#              │
#   PLS F3 ──▶ F1 (módulo M1.3) como ILS  ← recirculación
#
#   PLS F1 ──▶ SX (solución final)

def construir_grafo(ciclo, fecha):
    """Construye el grafo de ruteo para una fecha dada."""
    grafo = GrafoRuteo(nodos=[], aristas=[])

    for franja in ciclo.franjas:
        grafo.nodos.append(franja.id)
        for modulo in franja.modulos:
            ruteo = get_ruteo_vigente(modulo, fecha)
            if ruteo.tipo == "refino":
                grafo.aristas.append({
                    'origen': 'REFINO',
                    'destino': franja.id,
                    'modulo': modulo.id,
                    'vol': riego_dia.vol
                })
            else:  # ILS
                grafo.aristas.append({
                    'origen': ruteo.fuente_ils,
                    'destino': franja.id,
                    'modulo': modulo.id,
                    'vol': riego_dia.vol
                })

    return grafo
```

### 6.2 Balance de ILS entre Franjas

```python
# Verificación: el volumen de PLS usado como ILS no puede superar el PLS producido

for franja_origen in franjas:
    pls_producido = pls_franja_diario[franja_origen.id].vol_pls_m3

    vol_usado_ils = sum(
        riego.vol for riego in riegos_dia
        if riego.tipo == "ils" and riego.fuente_ils == franja_origen.id
    )

    if vol_usado_ils > pls_producido * 1.1:  # tolerancia 10%
        alerta("PLS de {franja_origen.id} insuficiente para ILS asignado")

    pls_excedente = pls_producido - vol_usado_ils  # va a SX o se descarta
```

---

## 7. KPIs por Nivel

### 7.1 Por Módulo (gestión de riego)

| KPI | Unidad | Nota |
|-----|--------|------|
| Vol. acumulado aplicado | m³ | Directo |
| RL estimada del módulo | m³/t | Con tonelaje prorrateado por área |
| Días con refino | días | Conteo |
| Días con ILS | días | Conteo |
| Días en reposo | días | Sin riego |
| Ácido aplicado total | kg H₂SO₄ | Por tipo de solución |
| Fuentes de ILS recibidas | lista | Historial |
| Uniformidad vs otros módulos | ratio | rl_mod / rl_promedio_franja |

### 7.2 Por Franja (balance de masas — dato medido)

| KPI | Unidad | Nota |
|-----|--------|------|
| Cu contenido soluble | kg | Directo |
| Cu extraído acumulado | kg | **Medido** |
| Recuperación | % | **Medida directa** |
| RL total / refino / ILS | m³/t | Segregada |
| RL por fuente de ILS | m³/t | Detalle de origen |
| Cu extraído fase refino | kg | Segregado por dominancia |
| Cu extraído fase ILS | kg | Segregado por dominancia |
| Eficiencia refino vs ILS | kg Cu/m³ | Comparativo |
| Ácido consumido total | kg H₂SO₄ | Medido |
| Ácido descompuesto | kg por componente | Cu/Fe/Cl/SiO₂/Mn/NA |
| Ratio ácido/Cu acumulado | kg/kg | vs cut-off |
| % cierre balance ácido | % | Calidad |
| Velocidad de extracción | kg Cu/día | Tendencia |
| % módulos con refino vs ILS | % | Gestión de riego |
| Concentración entrada ponderada | g/L | Cu, acid, Fe, etc. |

### 7.3 Por Ciclo

| KPI | Unidad |
|-----|--------|
| Σ Cu extraído todas las franjas | kg |
| Recuperación global | % |
| RL promedio ponderada (por ton) | m³/t |
| Ratio ácido/Cu global | kg/kg |
| Distribución Cu por franja | % |
| Complejidad del ruteo | # cambios |
| PLS enviado a SX vs recirculado como ILS | m³ |

### 7.4 Por Pad (histórico)

| KPI | Unidad |
|-----|--------|
| Ciclos completados | # |
| Recuperación promedio por ciclo | % |
| Consumo ácido promedio | kg/kg Cu |
| Tonelaje acumulado | t |

---

## 8. Visualizaciones

### 8.1 Mapa del Pad (vista planta interactiva)

```
GRÁFICO 1: Mapa de calor del pad

┌─────────────────────────────────────────┐
│  ┌─────┬─────┬─────┐                   │
│  │ M1.1│ M1.2│ M1.3│  F1  Rec: 45%     │
│  │ 42% │ 48% │ 38% │       RL: 1.2     │
│  │  R  │  R  │  I  │                   │
│  └─────┴─────┴─────┘                   │
│  ┌─────┬─────┬─────┐                   │
│  │ M2.1│ M2.2│ M2.3│  F2  Rec: 62%     │
│  │  I  │  I  │  R  │       RL: 1.8     │
│  └─────┴─────┴─────┘                   │
│  ┌───────┬───────┐                      │
│  │  M3.1 │  M3.2 │     F3  Rec: 71%    │
│  │   I   │   I   │          RL: 2.1    │
│  └───────┴───────┘                      │
└─────────────────────────────────────────┘

Colores:   🟢 >60% rec   🟡 30-60%   🔴 <30%
Letras:    R=Refino  I=ILS
Click en módulo → detalle de riego
Click en franja → balance completo
```

```
GRÁFICO 2: Diagrama Sankey de flujo de soluciones

  REFINO ═══╤════▶ F1 (M1.1, M1.2)
            │
            ╘════▶ F2 (M2.3)

  PLS F2 ════════▶ F3 (M3.1, M3.2) como ILS

  PLS F3 ════════▶ F1 (M1.3) como ILS

  PLS F1 ════════▶ SX ════▶ (producto)

  Grosor de línea = volumen de flujo
  Color = [Cu] de la solución
```

### 8.2 Vista de Ciclo de Riego por Módulo

```
GRÁFICO 3: Timeline de tipo de solución por módulo (Gantt)

M1.1 │████ REFINO ████████████████████████████│
M1.2 │████ REFINO ████████████████████████████│
M1.3 │████ REF ███│▓▓▓ ILS(F3) ▓▓▓│░░ ILS(F2) ░░│
─────┼─────────────────────────────────────────
M2.1 │████ REF ███│▓▓▓▓▓▓ ILS(F1) ▓▓▓▓▓▓▓▓▓▓│
M2.2 │████ REF ███│▓▓▓▓▓▓ ILS(F1) ▓▓▓▓▓▓▓▓▓▓│
M2.3 │████████████ REFINO ████████████████████│
─────┼─────────────────────────────────────────
M3.1 │████ REF ██│▓▓▓▓▓▓▓▓ ILS(F2) ▓▓▓▓▓▓▓▓▓│
M3.2 │████ REF ██│▓▓▓▓▓▓▓▓ ILS(F2) ▓▓▓▓▓▓▓▓▓│
     └─────────────────────────────────────────
     Ene    Feb    Mar    Abr    May    Jun

     █ Refino   ▓ ILS(fuente)   ░ ILS(otra fuente)
```

```
GRÁFICO 4: Uniformidad de riego entre módulos de una franja

  RL (m³/t)
  2.0 │          ┌───┐
  1.5 │  ┌───┐   │   │  ┌───┐    ← promedio franja: 1.5
  1.0 │  │M1.│   │M1.│  │M1.│
  0.5 │  │ 1 │   │ 2 │  │ 3 │
  0.0 │  └───┘   └───┘  └───┘
      └──────────────────────────

  Alerta si desviación > 20% del promedio
```

### 8.3 Vista de Razón de Lixiviación

```
GRÁFICO 5: Recuperación vs RL por franja (normalizado)

  Rec%
  80│                              ___── F3 (más madura)
  60│                    ___──────/
  40│          ___──────/    ___── F2
  20│   ──────/    ___──────/
   0│──────/──────/________________ F1 (más fresca)
    └──────────────────────────────
    0    0.5    1.0    1.5    2.0   RL (m³/t)

    Con segmentos coloreados: ██ fase refino  ▓▓ fase ILS
```

```
GRÁFICO 6: RL desglosada por tipo y fuente (stacked bar por franja)

  F1  │██ 0.8 ██│▓▓ 0.3(F3) ▓▓│░░ 0.1(F2) ░░│  RL=1.2
  F2  │██████ 1.2 ██████│▓▓▓ 0.6(F1) ▓▓▓│     RL=1.8
  F3  │███ 0.5 ███│▓▓▓▓▓▓ 1.6(F2) ▓▓▓▓▓▓│     RL=2.1
      └──────────────────────────────────────
      █ Refino    ▓ ILS(fuente)    ░ ILS(otra)
```

```
GRÁFICO 7: Ratio ácido/Cu vs RL (por franja) con línea de cut-off

  Ratio
  kg/kg
  15│\  F1
  10│ \___
   5│     \____──── F2 ──────
   3│- - - - - - CUT-OFF - - - - - - ← F3 ya pasó
    └──────────────────────────
    0    0.5    1.0    1.5    2.0   RL (m³/t)
```

### 8.4 Vista de Balance por Franja

8. **Curva de recuperación vs tiempo** — Con marcas de cambios de ruteo
9. **Descomposición de ácido (stacked area)** — Cu / Fe / Cl⁻ / SiO₂ / Mn / NA
10. **Concentración entrada ponderada vs PLS** — Cu, acid, Fe side-by-side
11. **Proxys de ganga** — ΔFe, ΔCl⁻, ΔSiO₂, ΔMn con anotaciones de cambios ruteo
12. **Fe²⁺/Fe³⁺ en PLS** — Evolución redox

### 8.5 Vista Comparativa entre Franjas

13. **Heatmap Rec% vs RL** — Franja × RL_bin
14. **Scatter mineralogía vs consumo ácido** — Por franja
15. **Waterfall de contribución Cu por franja** — % del total del ciclo

---

## 9. Templates de Input Excel/CSV

### Hoja 1: "pads"

| id_pad | nombre | area_total_m2 |
|--------|--------|--------------|

### Hoja 2: "ciclos"

| id_ciclo | id_pad | numero_ciclo | n_franjas | fecha_inicio | fecha_fin | cut_off_acid_cu |
|----------|--------|-------------|-----------|-------------|----------|----------------|

### Hoja 3: "franjas"

| id_franja | id_ciclo | numero_franja | n_modulos | fecha_on | fecha_off | tonelaje_t | area_m2 | altura_m | ley_cu_total | ley_cu_soluble | ley_cu_residual | humedad_residual | pct_goethita | pct_jarosita | pct_clorita | pct_atacamita | pct_crisocola | pct_cuarzo | pct_arcillas | pct_mn_oxidos |
|-----------|----------|--------------|----------|----------|----------|-----------|---------|----------|-------------|---------------|----------------|-----------------|-------------|-------------|------------|-------------- |-------------- |-----------|-------------|-------------- |

### Hoja 4: "modulos"

| id_modulo | id_franja | numero_modulo | area_m2 |
|-----------|-----------|--------------|---------|

### Hoja 5: "ruteo"

| id_modulo | fecha_inicio | fecha_fin | tipo_solucion | fuente_ils | proporcion_flujo | notas |
|-----------|-------------|----------|--------------|-----------|-----------------|-------|

### Hoja 6: "riego_diario" (una fila por módulo por día)

| id_modulo | fecha | vol_aplicado_m3 | tasa_riego_lhm2 | cu_entrada_gpl | acid_entrada_gpl | fe_total_entrada_gpl | fe2_entrada_gpl | cl_entrada_gpl | sio2_entrada_gpl | mn_entrada_gpl |
|-----------|-------|----------------|----------------|---------------|-----------------|--------------------|--------------------|---------------|-----------------|---------------|

### Hoja 7: "pls_diario" (una fila por franja por día)

| id_franja | fecha | vol_pls_m3 | cu_pls_gpl | acid_pls_gpl | fe_total_pls_gpl | fe2_pls_gpl | cl_pls_gpl | sio2_pls_gpl | mn_pls_gpl |
|-----------|-------|-----------|-----------|-------------|-----------------|------------|-----------|-------------|-----------|

---

## 10. Estructura de Código

```
modules/
├── heap_franja/
│   ├── __init__.py
│   ├── models.py              # Pad, Ciclo, Franja, Modulo, Ruteo, DatosRiego, DatosPLS
│   ├── copper_balance.py      # Balance Cu directo por franja (entrada ponderada)
│   ├── acid_balance.py        # Descomposición ácido por componente
│   ├── weighted_input.py      # Cálculo de entrada ponderada desde módulos
│   ├── leach_ratio.py         # RL total/refino/ILS/por fuente, normalizada
│   ├── irrigation.py          # Gestión de ruteo, transiciones, uniformidad
│   ├── routing_graph.py       # Grafo de flujo entre franjas, Sankey, validación
│   ├── gangue_proxies.py      # Proxys de ganga, factores DRX
│   ├── kinetics.py            # Curvas Rec vs RL, proyección cut-off
│   ├── holdup.py              # Corrección holdup por franja
│   ├── reconciliation.py      # Sol vs sólidos
│   ├── aggregation.py         # Franja → ciclo → pad
│   ├── lifecycle.py           # Estados y transiciones
│   ├── dashboard_pad.py       # Vista mapa del pad + Sankey
│   ├── dashboard_franja.py    # Vistas de balance + RL + riego
│   ├── dashboard_compare.py   # Vistas comparativas
│   ├── validators.py          # Validaciones + alertas
│   └── config.py              # Factores estequiométricos editables
```

---

## 11. Validaciones

| Validación | Condición | Nivel |
|-----------|-----------|-------|
| PLS suficiente para ILS | vol_ILS_asignado ≤ vol_PLS_producido × 1.1 | Ciclo |
| Uniformidad módulos | RL_mod vs RL_prom_franja > 20% | Franja |
| Balance hídrico franja | abs(Σvol_mod - vol_PLS)/Σvol_mod > 20% | Franja |
| Ruteo coherente | Módulo tope no recibe ILS de sí mismo | Ciclo |
| Ruteo circular | Detectar loops (F1→F2→F1) | Ciclo |
| Consistencia química ILS | [Cu] entrada módulo ≈ [Cu] PLS franja fuente | Módulo |
| Fe especiado | Fe²⁺ > Fe_total | Día |
| Ácido no asignado | > 30% del total | Franja |
| Cut-off | ratio_acid_cu > cut_off | Franja/Ciclo |
| Recuperación | > 100% | Franja |
| Mineralogía | Σ minerales > 100% | Franja |

---

## 12. Google Sheets

| Hoja | Contenido | Granularidad |
|------|-----------|-------------|
| `pads` | Maestro | Estática |
| `ciclos` | Configuración | Por ciclo |
| `franjas` | Mineral + mineralogía | Por franja |
| `modulos` | Subdivisión de franjas | Por módulo |
| `ruteo` | Historial de asignaciones | Por cambio |
| `riego_diario` | Vol + química entrada por módulo | Diaria × módulo |
| `pls_diario` | Vol + química PLS por franja | Diaria × franja |
| `balance_cu` | Cu extraído acumulado | Diaria × franja |
| `balance_acid` | Descomposición ácido | Diaria × franja |
| `razon_lixiviacion` | RL desglosada | Diaria × franja |
| `grafo_ruteo` | Snapshot del grafo por fecha | Semanal |
| `config` | Factores editables | Global |
