"""Unit tests for amount parsing, currency detection, and arithmetic validation."""

from app.amounts import (
    detect_currency_in_text,
    parse_monetary_amount,
    validate_arithmetic,
)


def test_standard_us_uk_amount_parsing():
    """Parse numbers with commas as thousands separators and dot as decimal."""
    assert parse_monetary_amount("1,234.56") == 1234.56
    assert parse_monetary_amount("£361.60") == 361.60
    assert parse_monetary_amount("$ 1,250.00") == 1250.00
    assert parse_monetary_amount("433.92") == 433.92


def test_european_amount_parsing():
    """Parse numbers with dot as thousands separator and comma as decimal."""
    assert parse_monetary_amount("1.200,50 €") == 1200.50
    assert parse_monetary_amount("228,10 €") == 228.10
    assert parse_monetary_amount("1.428,60") == 1428.60


def test_jpy_integer_amounts_normalized_to_two_decimals():
    """Rule O5: Japanese yen amounts printed without decimals normalize to two-decimal precision."""
    val = parse_monetary_amount("¥150000")
    assert val == 150000.0
    assert f"{val:.2f}" == "150000.00"

    val_sub = parse_monetary_amount("1,000")
    assert val_sub == 1000.0
    assert f"{val_sub:.2f}" == "1000.00"


def test_percentage_rejection():
    """Tax rates with percentage signs must not be parsed as monetary amounts."""
    assert parse_monetary_amount("20%") is None
    assert parse_monetary_amount("19.5 %") is None


def test_currency_detection():
    """Detect symbols and textual ISO/colloquial currencies."""
    assert detect_currency_in_text("Total: £433.92") == "GBP"
    assert detect_currency_in_text("Amount: $1,250.00") == "USD"
    assert detect_currency_in_text("Betrag: 1.200,50 €") == "EUR"
    assert detect_currency_in_text("合計: ¥165000") == "JPY"
    assert detect_currency_in_text("Grand Total: Rs. 28,910.00") == "INR"
    assert detect_currency_in_text("Amount in INR") == "INR"
    assert detect_currency_in_text("Subtotal in Euros") == "EUR"
    assert detect_currency_in_text("Price in Pounds") == "GBP"


def test_arithmetic_validation_within_tolerance():
    """Rule O2: Arithmetic matching within 0.01 tolerance produces no warning."""
    valid, warn = validate_arithmetic(361.60, 72.32, 433.92)
    assert valid is True
    assert warn is None

    # Tolerance within 0.01 due to rounding
    valid_tol, warn_tol = validate_arithmetic(100.00, 10.005, 110.01)
    assert valid_tol is True
    assert warn_tol is None


def test_arithmetic_mismatch_produces_warning():
    """Rule O2: Difference > 0.01 produces warning describing the arithmetic mismatch."""
    valid, warn = validate_arithmetic(100.00, 20.00, 150.00)
    assert valid is False
    assert warn is not None
    assert "Arithmetic mismatch" in warn
    assert "100.00" in warn
    assert "20.00" in warn
    assert "150.00" in warn
