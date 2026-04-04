"""Generación de reportes Excel y PDF."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, Iterable

import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PALETTE = {
    "ink": colors.HexColor("#203246"),
    "copper": colors.HexColor("#b35c2e"),
    "water": colors.HexColor("#2d7f7a"),
    "gold": colors.HexColor("#d1a126"),
    "mist": colors.HexColor("#eef3f7"),
    "slate": colors.HexColor("#6b7785"),
    "line": colors.HexColor("#d7e0e8"),
}


def build_excel_report(raw_df: pd.DataFrame, leaching_df: pd.DataFrame, sx_df: pd.DataFrame, ew_df: pd.DataFrame, global_df: pd.DataFrame) -> bytes:
    """Construye un Excel simple con hojas por etapa."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        raw_df.to_excel(writer, sheet_name="data_mensual", index=False)
        leaching_df.to_excel(writer, sheet_name="lix", index=False)
        sx_df.to_excel(writer, sheet_name="sx", index=False)
        ew_df.to_excel(writer, sheet_name="ew", index=False)
        global_df.to_excel(writer, sheet_name="balance_global", index=False)
    return output.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=PALETTE["ink"],
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=PALETTE["slate"],
        ),
        "section": ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=PALETTE["ink"],
            spaceBefore=6,
            spaceAfter=6,
        ),
        "card_label": ParagraphStyle(
            "card_label",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=colors.white,
        ),
        "card_value": ParagraphStyle(
            "card_value",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=colors.white,
        ),
        "body": ParagraphStyle(
            "body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=PALETTE["ink"],
        ),
        "small": ParagraphStyle(
            "small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=PALETTE["slate"],
        ),
    }


def _format_periods(values: Iterable[object]) -> list[str]:
    periods: list[str] = []
    for value in values:
        try:
            periods.append(pd.Timestamp(value).strftime("%Y-%m"))
        except Exception:
            periods.append(str(value))
    return periods


def _build_kpi_card(label: str, value: str, background: colors.Color, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[Paragraph(label, styles["card_label"])], [Paragraph(value, styles["card_value"])]],
        colWidths=[8.1 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0, background),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _build_kpi_grid(summary: Dict[str, float], styles: dict[str, ParagraphStyle]) -> Table:
    cards = [
        _build_kpi_card("Cu alimentado total", f"{summary['cu_alimentado_total_t']:.1f} t", PALETTE["ink"], styles),
        _build_kpi_card("Cu cátodos total", f"{summary['cu_catodos_total_t']:.1f} t", PALETTE["water"], styles),
        _build_kpi_card("Recuperación global", f"{summary['recuperacion_global_pct']:.1f}%", PALETTE["copper"], styles),
        _build_kpi_card("Ácido makeup total", f"{summary['acid_makeup_total_t']:.1f} t", PALETTE["gold"], styles),
    ]
    grid = Table([[cards[0], cards[1]], [cards[2], cards[3]]], colWidths=[8.4 * cm, 8.4 * cm], hAlign="LEFT")
    grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return grid


def _build_volume_chart(global_df: pd.DataFrame) -> Drawing:
    periods = _format_periods(global_df["periodo"].tolist())
    drawing = Drawing(17.5 * cm, 7.2 * cm)
    drawing.add(String(0, 6.8 * cm, "Producción de cobre por período", fontName="Helvetica-Bold", fontSize=11, fillColor=PALETTE["ink"]))

    chart = VerticalBarChart()
    chart.x = 1.2 * cm
    chart.y = 0.8 * cm
    chart.height = 4.8 * cm
    chart.width = 14.8 * cm
    chart.data = [
        (global_df["cu_alimentado_kg"] / 1000.0).round(2).tolist(),
        (global_df["cu_depositado_kg"] / 1000.0).round(2).tolist(),
    ]
    chart.categoryAxis.categoryNames = periods
    chart.categoryAxis.labels.angle = 35
    chart.categoryAxis.labels.dy = -10
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7
    chart.barSpacing = 3
    chart.groupSpacing = 8
    chart.bars[0].fillColor = PALETTE["copper"]
    chart.bars[1].fillColor = PALETTE["water"]
    drawing.add(chart)
    drawing.add(String(13.7 * cm, 6.05 * cm, "Cu alimentado", fontName="Helvetica", fontSize=8, fillColor=PALETTE["copper"]))
    drawing.add(String(13.7 * cm, 5.65 * cm, "Cu cátodos", fontName="Helvetica", fontSize=8, fillColor=PALETTE["water"]))
    return drawing


def _build_recovery_chart(global_df: pd.DataFrame) -> Drawing:
    periods = _format_periods(global_df["periodo"].tolist())
    drawing = Drawing(17.5 * cm, 7.2 * cm)
    drawing.add(String(0, 6.8 * cm, "Recuperación global", fontName="Helvetica-Bold", fontSize=11, fillColor=PALETTE["ink"]))

    chart = HorizontalLineChart()
    chart.x = 1.1 * cm
    chart.y = 1.0 * cm
    chart.height = 4.6 * cm
    chart.width = 14.9 * cm
    chart.data = [global_df["recuperacion_global_pct"].round(2).tolist()]
    chart.categoryAxis.categoryNames = periods
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(100, float(global_df["recuperacion_global_pct"].max()) + 5)
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 8
    chart.lines[0].strokeColor = PALETTE["water"]
    chart.lines[0].strokeWidth = 2.2
    drawing.add(chart)
    drawing.add(Line(1.1 * cm, 1.0 * cm + (4.6 * cm * 0.7), 16.0 * cm, 1.0 * cm + (4.6 * cm * 0.7), strokeColor=PALETTE["gold"], strokeDashArray=[4, 2]))
    drawing.add(String(13.0 * cm, 6.0 * cm, "Banda objetivo", fontName="Helvetica", fontSize=8, fillColor=PALETTE["gold"]))
    return drawing


def _build_detail_table(global_df: pd.DataFrame, styles: dict[str, ParagraphStyle]) -> Table:
    latest = global_df.copy().tail(8)
    latest["periodo"] = _format_periods(latest["periodo"].tolist())
    rows = [["Período", "Cu alim. (t)", "Cu cát. (t)", "Rec. %", "Pérdidas (t)", "Ácido neto (t)", "kg/kg Cu"]]
    for _, row in latest.iterrows():
        rows.append(
            [
                str(row["periodo"]),
                f"{row['cu_alimentado_kg'] / 1000.0:.1f}",
                f"{row['cu_depositado_kg'] / 1000.0:.1f}",
                f"{row['recuperacion_global_pct']:.1f}",
                f"{row['cu_perdidas_kg'] / 1000.0:.1f}",
                f"{row['acid_neto_kg'] / 1000.0:.1f}",
                f"{row['consumo_neto_acido_kgkg']:.2f}",
            ]
        )

    table = Table(rows, colWidths=[2.2 * cm, 2.2 * cm, 2.1 * cm, 1.6 * cm, 2.2 * cm, 2.2 * cm, 1.8 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PALETTE["ink"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, PALETTE["line"]),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALETTE["mist"]]),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_pdf_report(summary: Dict[str, float], global_df: pd.DataFrame) -> bytes:
    """Construye un PDF ejecutivo con KPIs, gráficos y detalle tabular."""
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.2 * cm,
        title="Balance de Masas Cu/H2SO4",
    )
    styles = _styles()
    global_prepared = global_df.copy()
    story = [
        Paragraph("Reporte Ejecutivo — Balance de Masas Cu/H2SO4", styles["title"]),
        Paragraph(
            f"Cadena LIX / SX / EW. Generado el {datetime.now().strftime('%d-%m-%Y %H:%M')} con cierre histórico consolidado.",
            styles["subtitle"],
        ),
        Spacer(1, 0.4 * cm),
        _build_kpi_grid(summary, styles),
        Spacer(1, 0.45 * cm),
        Paragraph(
            "Este documento resume la producción de cobre, recuperación global, pérdidas e intensidad de consumo ácido a nivel mensual.",
            styles["body"],
        ),
        Spacer(1, 0.35 * cm),
        _build_volume_chart(global_prepared),
        Spacer(1, 0.2 * cm),
        _build_recovery_chart(global_prepared),
        Spacer(1, 0.35 * cm),
        Paragraph("Detalle de períodos recientes", styles["section"]),
        _build_detail_table(global_prepared, styles),
        Spacer(1, 0.3 * cm),
        Paragraph(
            "Lectura rápida: un aumento simultáneo de pérdidas de Cu y consumo neto de ácido suele indicar deterioro del cierre metalúrgico o mayor carga de ganga reactiva.",
            styles["small"],
        ),
    ]
    document.build(story)
    return output.getvalue()
