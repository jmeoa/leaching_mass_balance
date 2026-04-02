"""
Balance de Masas Cu/H2SO4 — Planta Lix/SX/EW.

Dashboard Dash end to end apoyado en la data sintética de Iteración 1.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html
from plotly.subplots import make_subplots

from config import DEFAULT_CONFIG
from modules.heap_franja import (
    HeapFranjaDataset,
    calculate_acid_balance,
    calculate_copper_balance,
    calculate_leach_ratio,
    calculate_weighted_input,
)


BASE_DIR = Path(__file__).resolve().parent
SYNTHETIC_DIR = BASE_DIR / "data" / "synthetic"

PALETTE = {
    "copper": "#b35c2e",
    "acid": "#d1a126",
    "water": "#2d7f7a",
    "slate": "#213547",
    "ink": "#16212b",
    "mist": "#eef2ef",
    "sand": "#f5efe3",
}


@lru_cache(maxsize=1)
def load_dataset() -> HeapFranjaDataset:
    return HeapFranjaDataset.from_csv_dir(SYNTHETIC_DIR)


@lru_cache(maxsize=32)
def analyze_franja(id_franja: str) -> dict[str, object]:
    dataset = load_dataset()
    franja = dataset.get_franja(id_franja)
    riego_df = dataset.get_riego_by_franja(id_franja)
    pls_df = dataset.get_pls_by_franja(id_franja)
    modulos_df = dataset.get_modulos_by_franja(id_franja)
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
        "riego_df": riego_df,
        "pls_df": pls_df,
        "modulos_df": modulos_df,
        "weighted_df": weighted_df,
        "copper_daily_df": copper_daily_df,
        "copper_summary": copper_summary,
        "acid_daily_df": acid_daily_df,
        "acid_summary": acid_summary,
        "rl_daily_df": rl_daily_df,
        "rl_summary": rl_summary,
        "module_metrics_df": module_metrics_df,
    }


@lru_cache(maxsize=16)
def build_cycle_summary(id_ciclo: str) -> pd.DataFrame:
    dataset = load_dataset()
    rows = []
    for franja in dataset.get_franjas_by_ciclo(id_ciclo, operativas_only=True):
        if dataset.get_riego_by_franja(franja.id_franja).empty:
            continue
        analysis = analyze_franja(franja.id_franja)
        copper_summary = analysis["copper_summary"]
        acid_summary = analysis["acid_summary"]
        rl_summary = analysis["rl_summary"]
        rows.append(
            {
                "id_franja": franja.id_franja,
                "numero_franja": franja.numero_franja,
                "estado": "cerrada" if franja.recovery_from_residual_pct is not None else "en_riego",
                "recovery_pct": copper_summary.recovery_pct,
                "recovery_direct_pct": copper_summary.recovery_direct_pct,
                "recovery_residual_pct": copper_summary.recovery_residual_pct,
                "cu_extraido_kt": copper_summary.cu_extraido_reconciliado_kg / 1000.0,
                "acid_cierre_pct": acid_summary.acid_cierre_pct,
                "acid_ratio_kgkg": acid_summary.ratio_acid_cu_kgkg,
                "acid_consumido_t": acid_summary.acid_consumido_total_kg / 1000.0,
                "rl_total_m3_t": rl_summary.rl_total_m3_t,
                "rl_refino_m3_t": rl_summary.rl_refino_m3_t,
                "rl_ils_m3_t": rl_summary.rl_ils_m3_t,
                "fase_dominante": rl_summary.fase_dominante_global,
            }
        )
    return pd.DataFrame(rows).sort_values("numero_franja").reset_index(drop=True)


def format_kpi_value(value: float, kind: str = "number") -> str:
    if kind == "pct":
        return f"{value:,.1f}%"
    if kind == "kt":
        return f"{value:,.1f} kt"
    if kind == "acid":
        return f"{value:,.2f} kg/kg"
    if kind == "rl":
        return f"{value:,.2f} m³/t"
    if kind == "ton":
        return f"{value:,.1f} t"
    return f"{value:,.1f}"


def build_kpi_card(title: str, value: str, subtitle: str, tone: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(title, className="metric-label"),
                html.Div(value, className="metric-value"),
                html.Div(subtitle, className="metric-subtitle"),
            ]
        ),
        className=f"metric-card tone-{tone}",
    )


def empty_figure(title: str) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        template="plotly_white",
        title=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": "Sin datos disponibles",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": PALETTE["slate"]},
            }
        ],
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure


def figure_cycle_recovery(summary_df: pd.DataFrame) -> go.Figure:
    if summary_df.empty:
        return empty_figure("Recuperación y cierre de ácido por franja")
    figure = go.Figure()
    figure.add_bar(
        x=summary_df["id_franja"],
        y=summary_df["recovery_pct"],
        name="Recuperación reconciliada",
        marker_color=PALETTE["copper"],
    )
    figure.add_bar(
        x=summary_df["id_franja"],
        y=summary_df["acid_cierre_pct"],
        name="Cierre de ácido",
        marker_color=PALETTE["water"],
        opacity=0.8,
    )
    figure.update_layout(
        template="plotly_white",
        barmode="group",
        title="Recuperación y cierre de ácido por franja",
        yaxis_title="%",
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
        legend={"orientation": "h", "y": 1.12},
    )
    return figure


def figure_cycle_scatter(summary_df: pd.DataFrame) -> go.Figure:
    if summary_df.empty:
        return empty_figure("Relación ácido/Cu vs RL")
    figure = px.scatter(
        summary_df,
        x="rl_total_m3_t",
        y="acid_ratio_kgkg",
        size="cu_extraido_kt",
        color="acid_cierre_pct",
        hover_name="id_franja",
        color_continuous_scale=["#d9e8df", PALETTE["water"], PALETTE["copper"]],
        labels={
            "rl_total_m3_t": "RL total (m³/t)",
            "acid_ratio_kgkg": "Ratio ácido/Cu (kg/kg)",
            "acid_cierre_pct": "Cierre ácido (%)",
            "cu_extraido_kt": "Cu extraído (kt)",
        },
        title="Relación ácido/Cu vs RL",
    )
    figure.update_layout(
        template="plotly_white",
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
        coloraxis_colorbar={"title": "Cierre %"},
    )
    return figure


def figure_copper(daily_df: pd.DataFrame) -> go.Figure:
    if daily_df.empty:
        return empty_figure("Balance de cobre")
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Bar(
            x=daily_df["fecha"],
            y=daily_df["cu_extraido_corregido_kg"],
            name="Cu diario corregido",
            marker_color=PALETTE["copper"],
            opacity=0.35,
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=daily_df["fecha"],
            y=daily_df["recovery_direct_pct"],
            name="Recuperación directa",
            line={"color": PALETTE["slate"], "width": 2},
        ),
        secondary_y=True,
    )
    figure.add_trace(
        go.Scatter(
            x=daily_df["fecha"],
            y=daily_df["recovery_reconciled_pct"],
            name="Recuperación reconciliada",
            line={"color": PALETTE["water"], "width": 3},
        ),
        secondary_y=True,
    )
    if daily_df["recovery_residual_pct"].notna().any():
        figure.add_trace(
            go.Scatter(
                x=daily_df["fecha"],
                y=daily_df["recovery_residual_pct"],
                name="Control por ley residual",
                line={"color": PALETTE["acid"], "dash": "dash"},
            ),
            secondary_y=True,
        )
    figure.update_layout(
        template="plotly_white",
        title="Balance de cobre: extracción diaria y recuperación",
        margin={"l": 40, "r": 40, "t": 60, "b": 30},
        legend={"orientation": "h", "y": 1.08},
    )
    figure.update_yaxes(title_text="Cu extraído diario (kg)", secondary_y=False)
    figure.update_yaxes(title_text="Recuperación (%)", secondary_y=True)
    return figure


def figure_acid(daily_df: pd.DataFrame) -> go.Figure:
    if daily_df.empty:
        return empty_figure("Descomposición de ácido")
    figure = go.Figure()
    area_specs = [
        ("acid_por_cu_kg", "Ácido por Cu", PALETTE["copper"]),
        ("acid_por_fe_kg", "Ácido por Fe", "#6a847f"),
        ("acid_por_cl_kg", "Ácido por Cl-", "#d9b65c"),
        ("acid_por_sio2_kg", "Ácido por SiO2", "#8495a3"),
        ("acid_por_mn_kg", "Ácido por Mn", "#8d6f63"),
    ]
    first = True
    for column, label, color in area_specs:
        figure.add_trace(
            go.Scatter(
                x=daily_df["fecha"],
                y=daily_df[column],
                stackgroup="acid",
                mode="lines",
                line={"width": 0.5, "color": color},
                fillcolor=color,
                name=label,
                groupnorm=None,
            )
        )
        first = False
    figure.add_trace(
        go.Scatter(
            x=daily_df["fecha"],
            y=daily_df["acid_consumido_kg"],
            name="Consumo total de ácido",
            line={"color": PALETTE["ink"], "width": 3},
        )
    )
    figure.update_layout(
        template="plotly_white",
        title="Descomposición diaria del consumo de ácido",
        yaxis_title="kg H2SO4/d",
        margin={"l": 40, "r": 20, "t": 60, "b": 30},
        legend={"orientation": "h", "y": 1.08},
    )
    return figure


def figure_rl(daily_df: pd.DataFrame) -> go.Figure:
    if daily_df.empty:
        return empty_figure("Razón de lixiviación")
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=daily_df["fecha"],
            y=daily_df["rl_total_acum_m3_t"],
            name="RL total",
            line={"color": PALETTE["slate"], "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=daily_df["fecha"],
            y=daily_df["rl_refino_acum_m3_t"],
            name="RL refino",
            line={"color": PALETTE["acid"], "width": 2},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=daily_df["fecha"],
            y=daily_df["rl_ils_acum_m3_t"],
            name="RL ILS",
            line={"color": PALETTE["water"], "width": 2},
        )
    )
    figure.update_layout(
        template="plotly_white",
        title="RL acumulada por tipo de solución",
        yaxis_title="m³/t",
        margin={"l": 40, "r": 20, "t": 60, "b": 30},
        legend={"orientation": "h", "y": 1.08},
    )
    return figure


def figure_modules(module_metrics_df: pd.DataFrame) -> go.Figure:
    if module_metrics_df.empty:
        return empty_figure("Uniformidad de riego por módulo")
    figure = go.Figure()
    figure.add_bar(
        x=module_metrics_df["id_modulo"],
        y=module_metrics_df["rl_refino_m3_t"],
        name="RL refino",
        marker_color=PALETTE["acid"],
    )
    figure.add_bar(
        x=module_metrics_df["id_modulo"],
        y=module_metrics_df["rl_ils_m3_t"],
        name="RL ILS",
        marker_color=PALETTE["water"],
    )
    figure.update_layout(
        template="plotly_white",
        barmode="stack",
        title="RL por módulo",
        yaxis_title="m³/t",
        margin={"l": 40, "r": 20, "t": 60, "b": 60},
        legend={"orientation": "h", "y": 1.08},
    )
    return figure


def cycle_table_records(summary_df: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    if summary_df.empty:
        return [], []
    table_df = summary_df.copy()
    table_df["recovery_pct"] = table_df["recovery_pct"].map(lambda value: f"{value:.1f}%")
    table_df["acid_cierre_pct"] = table_df["acid_cierre_pct"].map(lambda value: f"{value:.1f}%")
    table_df["acid_ratio_kgkg"] = table_df["acid_ratio_kgkg"].map(lambda value: f"{value:.2f}")
    table_df["rl_total_m3_t"] = table_df["rl_total_m3_t"].map(lambda value: f"{value:.2f}")
    table_df["cu_extraido_kt"] = table_df["cu_extraido_kt"].map(lambda value: f"{value:.1f}")
    columns = [
        {"name": "Franja", "id": "id_franja"},
        {"name": "Estado", "id": "estado"},
        {"name": "Recuperación", "id": "recovery_pct"},
        {"name": "Cierre ácido", "id": "acid_cierre_pct"},
        {"name": "Ratio ácido/Cu", "id": "acid_ratio_kgkg"},
        {"name": "RL total", "id": "rl_total_m3_t"},
        {"name": "Cu extraído (kt)", "id": "cu_extraido_kt"},
        {"name": "Fase dominante", "id": "fase_dominante"},
    ]
    return table_df[[column["id"] for column in columns]].to_dict("records"), columns


def module_table_records(module_metrics_df: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    if module_metrics_df.empty:
        return [], []
    table_df = module_metrics_df.copy()
    numeric_columns = [
        "vol_aplicado_total_m3",
        "rl_total_m3_t",
        "rl_refino_m3_t",
        "rl_ils_m3_t",
        "acid_refino_kg",
        "acid_ils_kg",
        "uniformidad_ratio",
    ]
    for column in numeric_columns:
        table_df[column] = table_df[column].map(lambda value: f"{value:.2f}")
    columns = [
        {"name": "Módulo", "id": "id_modulo"},
        {"name": "Volumen total (m³)", "id": "vol_aplicado_total_m3"},
        {"name": "RL total", "id": "rl_total_m3_t"},
        {"name": "RL refino", "id": "rl_refino_m3_t"},
        {"name": "RL ILS", "id": "rl_ils_m3_t"},
        {"name": "Días refino", "id": "dias_refino"},
        {"name": "Días ILS", "id": "dias_ils"},
        {"name": "Días reposo", "id": "dias_reposo"},
        {"name": "Uniformidad", "id": "uniformidad_ratio"},
        {"name": "Fuentes ILS", "id": "fuentes_ils"},
    ]
    return table_df[[column["id"] for column in columns]].to_dict("records"), columns


dataset = load_dataset()
cycle_options = [
    {
        "label": f"{ciclo.id_ciclo} · ciclo {ciclo.numero_ciclo} · {ciclo.estado}",
        "value": ciclo.id_ciclo,
    }
    for ciclo in dataset.get_ciclos()
]
default_cycle = cycle_options[0]["value"] if cycle_options else None
default_franjas = dataset.get_franjas_by_ciclo(default_cycle, operativas_only=True) if default_cycle else []
default_franja_options = [
    {
        "label": f"Franja {franja.numero_franja:02d} · {franja.id_franja}",
        "value": franja.id_franja,
    }
    for franja in default_franjas
]
default_franja = default_franjas[0].id_franja if default_franjas else None


app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Balance de Masas Cu/H2SO4",
)
server = app.server


app.layout = dbc.Container(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Hydrolix · Iteración 1", className="hero-kicker"),
                        html.H1(
                            "Balance de masas Cu/H2SO4 por franja horizontal",
                            className="hero-title",
                        ),
                        html.P(
                            "Dashboard operativo construido sobre el motor de cálculo y la base sintética. "
                            "Muestra recuperación de cobre, cierre de ácido, RL y métricas de riego por módulo.",
                            className="hero-copy",
                        ),
                    ],
                    className="hero-copy-wrap",
                ),
                html.Div(
                    [
                        html.Div("Fuente", className="hero-stat-label"),
                        html.Div("data/synthetic", className="hero-stat-value"),
                        html.Div(
                            "Recuperación reconciliada para franjas cerradas; directa para las que siguen en riego.",
                            className="hero-stat-note",
                        ),
                    ],
                    className="hero-stat-card",
                ),
            ],
            className="hero-shell",
        ),
        dbc.Card(
            dbc.CardBody(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Ciclo", className="control-label"),
                                dcc.Dropdown(
                                    id="cycle-dropdown",
                                    options=cycle_options,
                                    value=default_cycle,
                                    clearable=False,
                                ),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                html.Label("Franja", className="control-label"),
                                dcc.Dropdown(
                                    id="franja-dropdown",
                                    options=default_franja_options,
                                    value=default_franja,
                                    clearable=False,
                                ),
                            ],
                            md=6,
                        ),
                    ]
                )
            ),
            className="panel-card control-panel",
        ),
        html.Div(id="cycle-kpis", className="metric-grid"),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="cycle-recovery-figure"), lg=7),
                dbc.Col(dcc.Graph(id="cycle-scatter-figure"), lg=5),
            ],
            className="g-3",
        ),
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div("Detalle de franja", className="section-kicker"),
                    html.H2(id="franja-title", className="section-title"),
                    html.P(id="franja-note", className="section-note"),
                ]
            ),
            className="panel-card mt-3",
        ),
        html.Div(id="franja-kpis", className="metric-grid"),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="copper-figure"), xl=7),
                dbc.Col(dcc.Graph(id="acid-figure"), xl=5),
            ],
            className="g-3",
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="rl-figure"), xl=6),
                dbc.Col(dcc.Graph(id="module-figure"), xl=6),
            ],
            className="g-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("Resumen del ciclo", className="table-title"),
                                dash_table.DataTable(
                                    id="cycle-table",
                                    page_size=8,
                                    style_table={"overflowX": "auto"},
                                    style_cell={"padding": "10px", "textAlign": "left"},
                                    style_header={"fontWeight": "700"},
                                ),
                            ]
                        ),
                        className="panel-card",
                    ),
                    xl=6,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("Riego por módulo", className="table-title"),
                                dash_table.DataTable(
                                    id="module-table",
                                    page_size=10,
                                    style_table={"overflowX": "auto"},
                                    style_cell={"padding": "10px", "textAlign": "left"},
                                    style_header={"fontWeight": "700"},
                                ),
                            ]
                        ),
                        className="panel-card",
                    ),
                    xl=6,
                ),
            ],
            className="g-3 mb-4",
        ),
    ],
    fluid=True,
    className="app-shell",
)


@app.callback(
    Output("franja-dropdown", "options"),
    Output("franja-dropdown", "value"),
    Input("cycle-dropdown", "value"),
)
def update_franja_options(cycle_id: str | None):
    if not cycle_id:
        return [], None
    franjas = load_dataset().get_franjas_by_ciclo(cycle_id, operativas_only=True)
    options = [
        {
            "label": f"Franja {franja.numero_franja:02d} · {franja.id_franja}",
            "value": franja.id_franja,
        }
        for franja in franjas
    ]
    value = options[0]["value"] if options else None
    return options, value


@app.callback(
    Output("cycle-kpis", "children"),
    Output("cycle-recovery-figure", "figure"),
    Output("cycle-scatter-figure", "figure"),
    Output("cycle-table", "data"),
    Output("cycle-table", "columns"),
    Input("cycle-dropdown", "value"),
)
def update_cycle_dashboard(cycle_id: str | None):
    summary_df = build_cycle_summary(cycle_id) if cycle_id else pd.DataFrame()

    cycle_cards = []
    if not summary_df.empty:
        cycle_cards = [
            build_kpi_card(
                "Franjas activas con datos",
                str(len(summary_df)),
                f"Ciclo {cycle_id}",
                "slate",
            ),
            build_kpi_card(
                "Recuperación promedio",
                format_kpi_value(summary_df["recovery_pct"].mean(), "pct"),
                "Recuperación reconciliada",
                "copper",
            ),
            build_kpi_card(
                "Cierre ácido promedio",
                format_kpi_value(summary_df["acid_cierre_pct"].mean(), "pct"),
                "Meta > 70%",
                "water",
            ),
            build_kpi_card(
                "RL promedio",
                format_kpi_value(summary_df["rl_total_m3_t"].mean(), "rl"),
                "Acumulada por franja",
                "acid",
            ),
            build_kpi_card(
                "Cu extraído total",
                format_kpi_value(summary_df["cu_extraido_kt"].sum(), "kt"),
                "Escala de ciclo",
                "slate",
            ),
        ]

    cycle_table_data, cycle_table_columns = cycle_table_records(summary_df)

    return (
        cycle_cards,
        figure_cycle_recovery(summary_df),
        figure_cycle_scatter(summary_df),
        cycle_table_data,
        cycle_table_columns,
    )


@app.callback(
    Output("franja-title", "children"),
    Output("franja-note", "children"),
    Output("franja-kpis", "children"),
    Output("copper-figure", "figure"),
    Output("acid-figure", "figure"),
    Output("rl-figure", "figure"),
    Output("module-figure", "figure"),
    Output("module-table", "data"),
    Output("module-table", "columns"),
    Input("franja-dropdown", "value"),
)
def update_franja_dashboard(franja_id: str | None):

    if not franja_id:
        return (
            "Sin franja seleccionada",
            "",
            [],
            empty_figure("Balance de cobre"),
            empty_figure("Descomposición de ácido"),
            empty_figure("Razón de lixiviación"),
            empty_figure("Uniformidad de riego por módulo"),
            [],
            [],
        )

    analysis = analyze_franja(franja_id)
    franja = analysis["franja"]
    copper_summary = analysis["copper_summary"]
    acid_summary = analysis["acid_summary"]
    rl_summary = analysis["rl_summary"]

    franja_cards = [
        build_kpi_card(
            "Recuperación reconciliada",
            format_kpi_value(copper_summary.recovery_pct, "pct"),
            "Promedia control residual si la franja está cerrada",
            "copper",
        ),
        build_kpi_card(
            "Recuperación directa",
            format_kpi_value(copper_summary.recovery_direct_pct, "pct"),
            "Balance solución entrada/salida + holdup",
            "slate",
        ),
        build_kpi_card(
            "Cierre de ácido",
            format_kpi_value(acid_summary.acid_cierre_pct, "pct"),
            f"Factor DRX Fe: {acid_summary.factor_drx_fe:.2f}",
            "water",
        ),
        build_kpi_card(
            "Ratio ácido/Cu",
            format_kpi_value(acid_summary.ratio_acid_cu_kgkg, "acid"),
            f"Cut-off ciclo: {load_dataset().get_ciclo(franja.id_ciclo).cut_off_acid_cu:.2f}",
            "acid",
        ),
        build_kpi_card(
            "RL total",
            format_kpi_value(rl_summary.rl_total_m3_t, "rl"),
            f"Refino {rl_summary.rl_refino_m3_t:.2f} · ILS {rl_summary.rl_ils_m3_t:.2f}",
            "slate",
        ),
    ]

    franja_note = (
        "Franja cerrada: la recuperación reconciliada mezcla balance directo y control por ley residual."
        if franja.recovery_from_residual_pct is not None
        else "Franja aún en riego: la recuperación mostrada se apoya solo en el balance directo."
    )

    module_table_data, module_table_columns = module_table_records(analysis["module_metrics_df"])

    return (
        f"Franja {franja.numero_franja:02d} · {franja.id_franja}",
        franja_note,
        franja_cards,
        figure_copper(analysis["copper_daily_df"]),
        figure_acid(analysis["acid_daily_df"]),
        figure_rl(analysis["rl_daily_df"]),
        figure_modules(analysis["module_metrics_df"]),
        module_table_data,
        module_table_columns,
    )


if __name__ == "__main__":
    app.run(
        debug=DEFAULT_CONFIG.dash_debug,
        host=DEFAULT_CONFIG.dash_host,
        port=DEFAULT_CONFIG.dash_port,
    )
