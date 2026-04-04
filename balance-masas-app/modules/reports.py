"""Generación de reportes Excel y PDF."""

from __future__ import annotations

import io
from typing import Dict

import pandas as pd
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


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


def build_pdf_report(summary: Dict[str, float], global_df: pd.DataFrame) -> bytes:
    """Construye un PDF ejecutivo básico."""
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, height - 2.5 * cm, "Reporte Ejecutivo — Balance de Masas Cu/H2SO4")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(2 * cm, height - 3.3 * cm, "Resumen mensual de la cadena LIX / SX / EW")

    y = height - 5 * cm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y, "KPIs Consolidados")
    pdf.setFont("Helvetica", 10)
    y -= 0.8 * cm
    for label, value in [
        ("Cu alimentado total (t)", f"{summary['cu_alimentado_total_t']:.1f}"),
        ("Cu cátodos total (t)", f"{summary['cu_catodos_total_t']:.1f}"),
        ("Recuperación global (%)", f"{summary['recuperacion_global_pct']:.1f}"),
        ("Ácido makeup total (t)", f"{summary['acid_makeup_total_t']:.1f}"),
        ("Ácido neto total (t)", f"{summary['acid_neto_total_t']:.1f}"),
    ]:
        pdf.drawString(2.2 * cm, y, f"• {label}: {value}")
        y -= 0.6 * cm

    y -= 0.3 * cm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y, "Detalle por período")
    y -= 0.8 * cm
    pdf.setFont("Helvetica", 9)
    for _, row in global_df.head(10).iterrows():
        line = (
            f"{row['periodo']}  |  Rec. global {row['recuperacion_global_pct']:.1f}%"
            f"  |  Cu pérdidas {row['cu_perdidas_kg'] / 1000.0:.1f} t"
            f"  |  Consumo neto ácido {row['consumo_neto_acido_kgkg']:.2f} kg/kg"
        )
        pdf.drawString(2.2 * cm, y, line[:115])
        y -= 0.5 * cm
        if y < 2 * cm:
            pdf.showPage()
            y = height - 2.5 * cm
            pdf.setFont("Helvetica", 9)

    pdf.save()
    return output.getvalue()
