"""End-to-end integration tests for POST /extract endpoint with PDF uploads."""

import time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_extract_northwind_pdf():
    """Verify POST /extract on Northwind Traders synthetic invoice."""
    pdf_path = FIXTURES_DIR / "northwind_standard.pdf"
    assert pdf_path.exists(), "Test fixture must exist"

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("northwind_standard.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()

    # Exact contract keys
    expected_keys = {
        "vendor", "invoice_number", "invoice_date", "due_date",
        "currency", "subtotal", "tax", "total", "confidence", "warnings"
    }
    assert set(data.keys()) == expected_keys

    # Field values
    assert data["vendor"] == "Northwind Traders"
    assert data["invoice_number"] == "NW-1042"
    assert data["invoice_date"] == "2026-09-03"
    assert data["due_date"] == "2026-10-03"
    assert data["currency"] == "GBP"
    assert data["subtotal"] == 361.60
    assert data["tax"] == 72.32
    assert data["total"] == 433.92

    # Confidence dictionary keys
    conf_keys = {
        "vendor", "invoice_number", "invoice_date", "due_date",
        "currency", "subtotal", "tax", "total"
    }
    assert set(data["confidence"].keys()) == conf_keys
    for k, v in data["confidence"].items():
        assert isinstance(v, float)
        assert 0.0 <= v <= 1.0


def test_extract_kestrel_pdf_mdy():
    """Verify POST /extract on Kestrel Components (US month-first date)."""
    pdf_path = FIXTURES_DIR / "kestrel_components_mdy.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("kestrel_components_mdy.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()

    assert data["vendor"] == "Kestrel Components"
    assert data["invoice_number"] == "KC-9921"
    assert data["invoice_date"] == "2026-09-03"
    assert data["due_date"] == "2026-10-15"  # Printed due date wins over Net 30
    assert data["currency"] == "USD"
    assert data["subtotal"] == 1250.00
    assert data["tax"] == 100.00
    assert data["total"] == 1350.00
    assert any("Printed due date (2026-10-15) conflicts with payment terms Net 30" in w for w in data["warnings"])


def test_extract_meridian_pdf_german():
    """Verify POST /extract on Meridian Industrial with German dot dates and MWST."""
    pdf_path = FIXTURES_DIR / "meridian_industrial_german.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("meridian_industrial_german.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()

    assert data["vendor"] == "Meridian Industrial"
    assert data["invoice_number"] == "MI-2026-44"
    assert data["invoice_date"] == "2026-09-03"
    assert data["due_date"] == "2026-10-03"
    assert data["currency"] == "EUR"
    assert data["subtotal"] == 1200.50
    assert data["tax"] == 228.10
    assert data["total"] == 1428.60


def test_extract_sakura_jpy_pdf():
    """Verify POST /extract on Sakura Precision with JPY whole numbers."""
    pdf_path = FIXTURES_DIR / "sakura_precision_jpy.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("sakura_precision_jpy.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()

    assert data["vendor"] == "Sakura Precision"
    assert data["invoice_number"] == "SP-7712"
    assert data["currency"] == "JPY"
    assert data["subtotal"] == 150000.0
    assert data["tax"] == 15000.0
    assert data["total"] == 165000.0


def test_extract_pinecrest_inr_pdf():
    """Verify POST /extract on Pinecrest Packaging with Indian Rupee formatting."""
    pdf_path = FIXTURES_DIR / "pinecrest_packaging_inr.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("pinecrest_packaging_inr.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()

    assert data["vendor"] == "Pinecrest Packaging"
    assert data["invoice_number"] == "PP-IN-5501"
    assert data["invoice_date"] == "2026-08-25"
    assert data["due_date"] == "2026-09-24"
    assert data["currency"] == "INR"
    assert data["subtotal"] == 24500.00
    assert data["tax"] == 4410.00
    assert data["total"] == 28910.00


def test_extract_non_invoice_quotation_pdf():
    """Rule O4: Quotation PDF returns null business fields, vendor identified, warning present."""
    pdf_path = FIXTURES_DIR / "non_invoice_quotation.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("non_invoice_quotation.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()

    assert data["vendor"] == "Kestrel Components"
    assert data["invoice_number"] is None
    assert data["invoice_date"] is None
    assert data["due_date"] is None
    assert data["currency"] is None
    assert data["subtotal"] is None
    assert data["tax"] is None
    assert data["total"] is None
    assert data["confidence"]["invoice_number"] == 0.0
    assert any("Document detected as quotation (not an invoice)" in w for w in data["warnings"])


def test_extract_error_handling_non_pdf():
    """Non-PDF file rejected with HTTP 400."""
    response = client.post(
        "/extract",
        files={"file": ("test.txt", b"Hello world, not a pdf", "text/plain")},
    )
    assert response.status_code == 400
    assert "Only PDF documents are supported" in response.json()["detail"]


def test_extract_error_handling_corrupt_pdf():
    """Corrupt PDF rejected with HTTP 400."""
    response = client.post(
        "/extract",
        files={"file": ("corrupt.pdf", b"%PDF-1.4 corrupt data", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Corrupt or malformed PDF" in response.json()["detail"] or "Failed to read" in response.json()["detail"]


def test_extract_missing_file_upload():
    """Missing file upload rejected with HTTP 422 or 400."""
    response = client.post("/extract")
    assert response.status_code in [400, 422]


def test_extract_pdf_with_no_text_layer():
    """PDF with no extractable text layer returns HTTP 422."""
    from reportlab.pdfgen import canvas
    import io

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()  # Empty page with no text
    c.save()
    empty_pdf_bytes = buf.getvalue()

    response = client.post(
        "/extract",
        files={"file": ("empty.pdf", empty_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 422
    assert "no extractable text" in response.json()["detail"].lower()


def test_extract_arithmetic_mismatch_pdf():
    """PDF with arithmetic mismatch preserves printed values and includes warning."""
    pdf_path = FIXTURES_DIR / "arithmetic_mismatch.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("arithmetic_mismatch.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()
    assert data["vendor"] == "Northwind Traders"
    assert data["subtotal"] == 100.00
    assert data["tax"] == 20.00
    assert data["total"] == 150.00
    assert any("Arithmetic mismatch" in w for w in data["warnings"])


def test_extract_inferred_currency_meridian_pdf():
    """PDF with no printed currency infers vendor default with lower confidence and warning."""
    pdf_path = FIXTURES_DIR / "missing_currency_meridian.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("missing_currency_meridian.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()
    assert data["vendor"] == "Meridian Industrial"
    assert data["currency"] == "EUR"
    assert data["confidence"]["currency"] == 0.60
    assert any("Currency inferred from vendor default (EUR)" in w for w in data["warnings"])


def test_extract_delivery_note_pdf():
    """Delivery note PDF returns vendor and null fields."""
    pdf_path = FIXTURES_DIR / "non_invoice_delivery_note.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("non_invoice_delivery_note.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()
    assert data["vendor"] == "Blue Harbour Logistics"
    assert data["invoice_number"] is None
    assert any("Document detected as delivery note" in w for w in data["warnings"])


def test_extract_statement_pdf():
    """Statement of account PDF returns vendor and null fields."""
    pdf_path = FIXTURES_DIR / "non_invoice_statement.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("non_invoice_statement.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()
    assert data["vendor"] == "Pinecrest Packaging"
    assert data["invoice_number"] is None
    assert any("Document detected as statement of account" in w for w in data["warnings"])


def test_extract_kestrel_0311_appendix_n():
    """Verify Appendix N Example 2 (kestrel_0311.pdf) matches the exact contract values."""
    pdf_path = FIXTURES_DIR / "kestrel_0311.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("kestrel_0311.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()

    assert data["vendor"] == "Kestrel Components"
    assert data["invoice_number"] == "KC-0311"
    assert data["invoice_date"] == "2026-09-03"
    assert data["due_date"] == "2026-10-03"
    assert data["currency"] == "USD"
    assert data["subtotal"] == 225.80
    assert data["tax"] == 16.37
    assert data["total"] == 242.17
    assert "Date 9/3/26 read as month-first (US vendor)." in data["warnings"]
    assert "Due date derived from terms Net 30." in data["warnings"]


def test_extract_unknown_vendor_example_3():
    """Verify Example 3 (unknown_vendor.pdf) matches the brief's contract."""
    pdf_path = FIXTURES_DIR / "unknown_vendor.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        response = client.post("/extract", files={"file": ("unknown_vendor.pdf", f, "application/pdf")})

    assert response.status_code == 200
    data = response.json()

    assert data["vendor"] == "unknown"
    assert data["invoice_number"] == "7781"
    assert data["invoice_date"] == "2026-08-21"
    assert data["due_date"] is None
    assert data["currency"] == "INR"
    assert data["subtotal"] == 12000.0
    assert data["tax"] == 2160.0
    assert data["total"] == 14160.0
    assert "Vendor name not in the canonical list." in data["warnings"]
    assert "No due date or payment terms found." in data["warnings"]
    assert data["confidence"]["vendor"] == 0.20
    assert data["confidence"]["due_date"] == 0.0


def test_extract_performance_under_one_second():
    """Request latency is well under 1 second on CPU."""
    pdf_path = FIXTURES_DIR / "northwind_standard.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    start_time = time.perf_counter()
    response = client.post("/extract", files={"file": ("northwind_standard.pdf", content, "application/pdf")})
    elapsed = time.perf_counter() - start_time

    assert response.status_code == 200
    assert elapsed < 1.0, f"Extraction took {elapsed:.3f}s, expected < 1.0s"
    print(f"\nMeasured extraction latency: {elapsed * 1000:.2f} ms")


