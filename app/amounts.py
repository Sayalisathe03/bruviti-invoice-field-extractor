"""Amount normalization, currency identification, and decimal arithmetic validation."""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Tuple

CURRENCY_SYMBOLS_MAP = {
    "£": "GBP",
    "€": "EUR",
    "¥": "JPY",
    "₹": "INR",
    "$": "USD",
}

CURRENCY_TEXT_MAP = {
    "gbp": "GBP",
    "usd": "USD",
    "eur": "EUR",
    "jpy": "JPY",
    "inr": "INR",
    "rs": "INR",
    "rs.": "INR",
    "rupee": "INR",
    "rupees": "INR",
    "inr.": "INR",
    "pound": "GBP",
    "pounds": "GBP",
    "euro": "EUR",
    "euros": "EUR",
    "yen": "JPY",
}


def detect_currency_in_text(text: str) -> Optional[str]:
    """Detect explicit currency symbol or textual ISO code in a given string."""
    # Check symbols first
    for symbol, code in CURRENCY_SYMBOLS_MAP.items():
        if symbol in text:
            return code

    # Check textual codes / words with word boundaries
    lowered = text.lower()
    for token, code in CURRENCY_TEXT_MAP.items():
        pattern = r"\b" + re.escape(token) + r"\b"
        if re.search(pattern, lowered):
            return code

    return None


def parse_monetary_amount(raw_str: str) -> Optional[float]:
    """
    Parse a numeric string into a two-decimal float, handling various international formats:
    - 1,234.56 (US / UK / standard)
    - 1.234,56 (European)
    - 1 234.56 or 1 234,56 (space grouped)
    - 1000 or 1,000 (integer / JPY)
    """
    if not raw_str or not raw_str.strip():
        return None

    cleaned = raw_str.strip()

    # Reject tax/company registration numbers (e.g. GB987654321, 07AAAAA0000A1Z5)
    if re.search(r"\b[A-Z]{2}\d{5,}\b", cleaned) or re.search(r"\b\d{2}[A-Z]{5}\d{4}", cleaned):
        return None

    # First, strip out percentage annotations like (20%), 19.5%, etc.
    cleaned = re.sub(r"\(?\s*\d+(?:\.\d+)?\s*%\s*\)?", " ", cleaned)

    # If nothing with digits is left, it was purely a percentage rate
    if not any(ch.isdigit() for ch in cleaned):
        return None

    # Strip currency symbols and textual tokens
    cleaned = re.sub(
        r"(?i)\b(?:usd|gbp|eur|jpy|inr|rupees?|pounds?|euros?|yen)\b|rs\.?|[£$€¥₹]",
        " ",
        cleaned,
    )
    cleaned = cleaned.strip()

    # Match numeric portion: digits, dots, commas, spaces
    m = re.search(r"[-+]?\s*[\d\s.,]+", cleaned)
    if not m:
        return None

    num_str = m.group(0).replace(" ", "").strip()
    # Strip any stray leading or trailing punctuation from abbreviations/colons
    num_str = num_str.strip(".,;:-")
    if not num_str or not any(ch.isdigit() for ch in num_str):
        return None

    # Determine decimal separator vs grouping separator
    # European style: 1.234,56 or 1234,56
    if "," in num_str and "." in num_str:
        if num_str.rfind(",") > num_str.rfind("."):
            # Dot is thousand, comma is decimal: e.g. 1.234,56 -> 1234.56
            num_str = num_str.replace(".", "").replace(",", ".")
        else:
            # Comma is thousand, dot is decimal: e.g. 1,234.56 -> 1234.56
            num_str = num_str.replace(",", "")
    elif "," in num_str:
        # Only commas: could be decimal (e.g. 1234,56) or grouping (1,000 or 1,000,000)
        parts = num_str.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            # Likely decimal comma (e.g. 12,50 or 1234,5)
            num_str = parts[0] + "." + parts[1]
        else:
            # Grouping separator (e.g. 1,000 or 1,000,000)
            num_str = "".join(parts)
    elif "." in num_str:
        # Only dots: could be decimal (1234.56) or European grouping (1.000 or 1.000.000)
        parts = num_str.split(".")
        if len(parts) > 2:
            # Multiple dots: grouping
            num_str = "".join(parts)

    try:
        dec = Decimal(num_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(dec)
    except (InvalidOperation, ValueError):
        return None


def validate_arithmetic(
    subtotal: Optional[float], tax: Optional[float], total: Optional[float]
) -> Tuple[bool, Optional[str]]:
    """
    Validate Rule O2: subtotal + tax == total (tolerance 0.01).

    Returns:
        (is_consistent, warning_or_none)
    """
    if subtotal is None or tax is None or total is None:
        return True, None

    dec_subtotal = Decimal(str(subtotal))
    dec_tax = Decimal(str(tax))
    dec_total = Decimal(str(total))

    diff = abs((dec_subtotal + dec_tax) - dec_total)
    if diff > Decimal("0.01"):
        warning = (
            f"Arithmetic mismatch: subtotal ({subtotal:.2f}) + tax ({tax:.2f}) "
            f"!= total ({total:.2f})."
        )
        return False, warning

    return True, None
