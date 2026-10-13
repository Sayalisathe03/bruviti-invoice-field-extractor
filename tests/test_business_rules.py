"""Tests for required business rules O1, O2, O3, O4, and O5."""

from app.extractor import extract_invoice


def test_rule_o1_terms_derive_due_date():
    """Rule O1: When no printed due date is present, terms derive due date with warning."""
    text = """
    Northwind Traders Ltd
    TAX INVOICE
    Invoice Number: NW-1001
    Invoice Date: 2026-09-01
    Payment Terms: Net 30
    Subtotal: £100.00
    Tax: £20.00
    Total: £120.00
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    resp = extract_invoice(text, lines)

    assert resp.due_date == "2026-10-01"
    assert resp.confidence.due_date > 0.8
    assert any("Due date derived from terms Net 30" in w for w in resp.warnings)


def test_rule_o1_conflicting_printed_due_date_wins():
    """Rule O1: When printed due date conflicts with terms, printed due date wins with warning."""
    text = """
    Kestrel Components Inc
    INVOICE
    Invoice Number: KC-2002
    Invoice Date: 2026-09-01
    Payment Terms: Net 30
    Due Date: 2026-10-15
    Subtotal: $100.00
    Tax: $10.00
    Total: $110.00
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    resp = extract_invoice(text, lines)

    # Printed due date is 2026-10-15, derived would be 2026-10-01
    assert resp.due_date == "2026-10-15"
    assert any("Printed due date (2026-10-15) conflicts with payment terms Net 30" in w for w in resp.warnings)


def test_rule_o2_arithmetic_mismatch_preserves_values_with_warning():
    """Rule O2: Arithmetic mismatch preserves printed values and adds warning without adjustments."""
    text = """
    Northwind Traders
    Invoice No: NW-999
    Invoice Date: 2026-09-01
    Due Date: 2026-09-30
    Subtotal: £100.00
    Tax: £20.00
    Total: £150.00
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    resp = extract_invoice(text, lines)

    # Values must remain unchanged
    assert resp.subtotal == 100.00
    assert resp.tax == 20.00
    assert resp.total == 150.00
    assert any("Arithmetic mismatch: subtotal (100.00) + tax (20.00) != total (150.00)" in w for w in resp.warnings)


def test_rule_o3_missing_currency_inferred_for_known_vendor():
    """Rule O3: Missing currency marker infers known vendor default with lower confidence and warning."""
    text = """
    Meridian Industrial GmbH
    Invoice Number: MI-777
    Invoice Date: 2026-09-01
    Due Date: 2026-09-30
    Subtotal: 100.00
    Tax: 19.00
    Total: 119.00
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    resp = extract_invoice(text, lines)

    assert resp.vendor == "Meridian Industrial"
    assert resp.currency == "EUR"
    assert resp.confidence.currency == 0.60
    assert any("Currency inferred from vendor default (EUR)" in w for w in resp.warnings)


def test_rule_o3_missing_currency_unknown_vendor_returns_null():
    """Rule O3: Unknown vendor with no currency returns null and warning."""
    text = """
    Solaris Dynamics Corp
    Invoice Number: SD-100
    Invoice Date: 2026-09-01
    Due Date: 2026-09-30
    Subtotal: 100.00
    Tax: 10.00
    Total: 110.00
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    resp = extract_invoice(text, lines)

    assert resp.vendor == "unknown"
    assert resp.currency is None
    assert resp.confidence.currency == 0.0
    assert any("No currency detected for unknown vendor" in w for w in resp.warnings)


def test_rule_o4_non_invoice_quotation():
    """Rule O4: Quotation returns null business fields, vendor identified, warning present."""
    text = """
    Kestrel Components Inc
    PRICE QUOTATION
    Quote Number: Q-550
    Date: 2026-09-01
    Subtotal: $500.00
    Tax: $50.00
    Total: $550.00
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    resp = extract_invoice(text, lines)

    assert resp.vendor == "Kestrel Components"
    assert resp.confidence.vendor > 0.8
    # All 7 other business fields must be null
    assert resp.invoice_number is None
    assert resp.invoice_date is None
    assert resp.due_date is None
    assert resp.currency is None
    assert resp.subtotal is None
    assert resp.tax is None
    assert resp.total is None
    assert resp.confidence.invoice_number == 0.0
    assert resp.confidence.total == 0.0
    assert any("Document detected as quotation (not an invoice)" in w for w in resp.warnings)


def test_rule_o4_non_invoice_delivery_note():
    """Rule O4: Delivery note returns null business fields and document warning."""
    text = """
    Blue Harbour Logistics
    DELIVERY NOTE
    Delivery Note #: DN-991
    Dispatch Date: 2026-06-12
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    resp = extract_invoice(text, lines)

    assert resp.vendor == "Blue Harbour Logistics"
    assert resp.invoice_number is None
    assert any("Document detected as delivery note (not an invoice)" in w for w in resp.warnings)


def test_rule_o5_jpy_normalization():
    """Rule O5: Japanese yen whole integer amounts normalize to two-decimal precision."""
    text = """
    Sakura Precision KK
    INVOICE
    Invoice No: SP-101
    Invoice Date: 2026-04-10
    Due Date: 2026-05-10
    Subtotal: ¥150000
    Consumption Tax: ¥15000
    Total Due: ¥165000
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    resp = extract_invoice(text, lines)

    assert resp.currency == "JPY"
    assert resp.subtotal == 150000.0
    assert resp.tax == 15000.0
    assert resp.total == 165000.0
