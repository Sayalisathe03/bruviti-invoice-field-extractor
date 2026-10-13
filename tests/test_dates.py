"""Unit tests for date parsing, vendor locale rules, ambiguity warnings, and payment terms."""

from app.dates import (
    derive_due_date_from_terms,
    extract_payment_terms,
    parse_flexible_date,
    parse_numeric_date,
    parse_textual_month_date,
)


def test_ambiguous_uk_date_day_first():
    """Ambiguous 03/09/2026 is parsed as day-first for UK vendor (3 September 2026)."""
    iso_date, warning = parse_flexible_date("03/09/2026", vendor_country="United Kingdom", date_order="DMY")
    assert iso_date == "2026-09-03"
    assert warning is not None
    assert "day-first" in warning
    assert "UK vendor" in warning


def test_ambiguous_us_date_month_first():
    """Ambiguous 9/3/26 is parsed as month-first for US vendor (3 September 2026)."""
    iso_date, warning = parse_flexible_date("9/3/26", vendor_country="United States", date_order="MDY")
    assert iso_date == "2026-09-03"
    assert warning is not None
    assert "month-first" in warning
    assert "US vendor" in warning or "United States" in warning


def test_ambiguous_unknown_vendor_fallback_policy():
    """Ambiguous date for unknown vendor defaults to day-first with documented policy warning."""
    iso_date, warning = parse_flexible_date("03/09/2026", vendor_country=None, date_order="DMY")
    assert iso_date == "2026-09-03"
    assert warning is not None
    assert "day-first" in warning
    assert "unknown vendor" in warning


def test_unambiguous_day_greater_than_12():
    """Dates where day > 12 are unambiguous and require no ambiguity warning."""
    iso_date, warning = parse_flexible_date("25/08/2026", vendor_country="United Kingdom", date_order="DMY")
    assert iso_date == "2026-08-25"
    assert warning is None

    iso_date_us, warning_us = parse_flexible_date("08/25/2026", vendor_country="United States", date_order="MDY")
    assert iso_date_us == "2026-08-25"
    assert warning_us is None


def test_german_and_japanese_dot_dates():
    """German/Japanese dot-separated formats: DD.MM.YYYY and YYYY.MM.DD."""
    iso_dmy, _ = parse_flexible_date("03.09.2026", vendor_country="Germany", date_order="DMY")
    assert iso_dmy == "2026-09-03"

    iso_ymd, warn_ymd = parse_flexible_date("2026.09.03", vendor_country="Japan", date_order="DMY")
    assert iso_ymd == "2026-09-03"
    assert warn_ymd is None


def test_textual_month_formats():
    """Textual month names and abbreviations in various orders."""
    assert parse_textual_month_date("3 September 2026") == "2026-09-03"
    assert parse_textual_month_date("September 3, 2026") == "2026-09-03"
    assert parse_textual_month_date("Sep 3, 2026") == "2026-09-03"
    assert parse_textual_month_date("3rd Sep 2026") == "2026-09-03"
    assert parse_textual_month_date("03-Sep-2026") == "2026-09-03"
    assert parse_textual_month_date("2026 September 3") == "2026-09-03"


def test_invalid_dates_return_none():
    """Invalid dates must return None, not a guessed date."""
    assert parse_flexible_date("not-a-date")[0] is None
    assert parse_flexible_date("32/13/2026")[0] is None
    assert parse_flexible_date("2026-02-30")[0] is None


def test_payment_terms_parsing_and_calculation():
    """Test extracting payment terms and calculating due date (Rule O1)."""
    days1, label1 = extract_payment_terms("Payment terms: Net 30")
    assert days1 == 30
    assert label1 == "Net 30"
    assert derive_due_date_from_terms("2026-09-03", days1) == "2026-10-03"

    days2, label2 = extract_payment_terms("Balance due in 15 days")
    assert days2 == 15
    assert derive_due_date_from_terms("2026-09-03", days2) == "2026-09-18"

    days3, label3 = extract_payment_terms("within 60 days of invoice date")
    assert days3 == 60
    assert derive_due_date_from_terms("2026-01-01", days3) == "2026-03-02"
