from __future__ import annotations

import io

from fastapi.testclient import TestClient

from backend.api.main import app
from modules.data_loader import build_synthetic_monthly_input


client = TestClient(app)


def test_healthcheck():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_monthly_overview_returns_summary_and_tables():
    response = client.get("/api/monthly/overview")
    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "tables" in payload
    assert payload["tables"]["global"]


def test_heap_franja_endpoint_returns_detail():
    response = client.get("/api/heap/franja/PAD-01-C01-F02")
    assert response.status_code == 200
    payload = response.json()
    assert payload["franja"]["id"] == "PAD-01-C01-F02"
    assert payload["moduleMetrics"]


def test_heap_pad_endpoint_returns_cycle_payload():
    response = client.get("/api/heap/pad/PAD-01-C01")
    assert response.status_code == 200
    payload = response.json()
    assert payload["cycleSummary"]
    assert payload["lifecycle"]


def test_template_and_reports_endpoints_return_downloads():
    template_response = client.get("/api/template")
    excel_response = client.get("/api/reports/excel")
    pdf_response = client.get("/api/reports/pdf")

    assert template_response.status_code == 200
    assert excel_response.status_code == 200
    assert pdf_response.status_code == 200
    assert excel_response.content[:2] == b"PK"
    assert pdf_response.content[:4] == b"%PDF"


def test_upload_preview_endpoint_accepts_monthly_csv():
    monthly_df = build_synthetic_monthly_input().copy()
    monthly_df["periodo"] = monthly_df["periodo"].dt.strftime("%Y-%m")
    buffer = io.StringIO()
    monthly_df.to_csv(buffer, index=False)

    response = client.post(
        "/api/upload/preview",
        files={"file": ("monthly_input.csv", buffer.getvalue(), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rows"] == len(monthly_df)
    assert payload["valid"] is True
