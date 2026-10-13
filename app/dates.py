"""Date parsing, ambiguity resolution, vendor locale rules, and payment terms calculation."""

import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

MONTH_NAMES = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_MONTH_REGEX_STR = (
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
)

# Payment terms patterns: e.g. "Net 30", "30 days", "due in 30 days", "within 30 days", "Net 15 days"
PAYMENT_TERMS_PATTERNS = [
    re.compile(r"\bnet\s*(\d{1,3})\s*(?:days)?\b", flags=re.IGNORECASE),
    re.compile(r"\bdue\s+in\s+(\d{1,3})\s+days\b", flags=re.IGNORECASE),
    re.compile(r"\bwithin\s+(\d{1,3})\s+days\b", flags=re.IGNORECASE),
    re.compile(r"\bpayment\s+terms[:\s]+(\d{1,3})\s+days\b", flags=re.IGNORECASE),
    re.compile(r"\bterms[:\s]+(?:net\s*)?(\d{1,3})\s+days\b", flags=re.IGNORECASE),
    re.compile(r"\b(\d{1,3})\s+days\s+(?:net|from\s+invoice)\b", flags=re.IGNORECASE),
    re.compile(r"\b(\d{1,3})\s+days\b", flags=re.IGNORECASE),
]


def expand_year(year: int) -> int:
    """Expand a 2-digit year into a 4-digit year."""
    if year < 100:
        return 2000 + year if year < 70 else 1900 + year
    return year


def extract_payment_terms(text: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Search for payment terms in text (e.g. Net 30, due in 30 days).

    Returns:
        (days, term_label_string)
    """
    for pattern in PAYMENT_TERMS_PATTERNS:
        match = pattern.search(text)
        if match:
            days = int(match.group(1))
            raw_match = match.group(0).strip()
            # Standardize label
            if "net" in raw_match.lower():
                term_label = f"Net {days}"
            else:
                term_label = raw_match
            return days, term_label
    return None, None


def derive_due_date_from_terms(invoice_date_iso: str, days: int) -> Optional[str]:
    """Calculate due date from invoice date + calendar days."""
    try:
        dt = datetime.strptime(invoice_date_iso, "%Y-%m-%d").date()
        due = dt + timedelta(days=days)
        return due.isoformat()
    except Exception:
        return None


def parse_textual_month_date(raw_date: str) -> Optional[str]:
    """Parse dates with textual months like '3 September 2026', 'September 3, 2026', '03-Sep-2026'."""
    text = raw_date.strip().lower()
    # Remove ordinal suffixes: 1st, 2nd, 3rd, 4th
    text = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", text)
    # Normalize separators
    text = re.sub(r"[,\-_/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Pattern 1: Day Month Year (e.g. "3 september 2026")
    m1 = re.match(rf"^(\d{{1,2}})\s+({_MONTH_REGEX_STR})\s+(\d{{2,4}})$", text)
    if m1:
        day = int(m1.group(1))
        month = MONTH_NAMES.get(m1.group(2))
        year = expand_year(int(m1.group(3)))
        if month:
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                return None

    # Pattern 2: Month Day Year (e.g. "september 3 2026")
    m2 = re.match(rf"^({_MONTH_REGEX_STR})\s+(\d{{1,2}})\s+(\d{{2,4}})$", text)
    if m2:
        month = MONTH_NAMES.get(m2.group(1))
        day = int(m2.group(2))
        year = expand_year(int(m2.group(3)))
        if month:
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                return None

    # Pattern 3: Year Month Day (e.g. "2026 september 3")
    m3 = re.match(rf"^(\d{{4}})\s+({_MONTH_REGEX_STR})\s+(\d{{1,2}})$", text)
    if m3:
        year = int(m3.group(1))
        month = MONTH_NAMES.get(m3.group(2))
        day = int(m3.group(3))
        if month:
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                return None

    return None


def parse_numeric_date(
    raw_date: str, vendor_country: Optional[str] = None, date_order: str = "DMY"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a numeric date string using vendor date order rules.

    Returns:
        (iso_date, ambiguity_warning)
    """
    text = raw_date.strip()

    # Case 1: YYYY-MM-DD or YYYY.MM.DD or YYYY/MM/DD (unambiguous ISO-like)
    m_iso = re.match(r"^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$", text)
    if m_iso:
        y = int(m_iso.group(1))
        m = int(m_iso.group(2))
        d = int(m_iso.group(3))
        try:
            return date(y, m, d).isoformat(), None
        except ValueError:
            return None, None

    # Case 2: DD/MM/YYYY, MM/DD/YYYY, DD.MM.YYYY or 2-digit years
    m_split = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$", text)
    if m_split:
        p1 = int(m_split.group(1))
        p2 = int(m_split.group(2))
        y = expand_year(int(m_split.group(3)))

        # Check if p1 or p2 cannot be a month (> 12)
        if p1 > 12 and p2 <= 12:
            # Must be Day-Month-Year
            try:
                return date(y, p2, p1).isoformat(), None
            except ValueError:
                return None, None
        elif p2 > 12 and p1 <= 12:
            # Must be Month-Day-Year
            try:
                return date(y, p1, p2).isoformat(), None
            except ValueError:
                return None, None
        elif p1 <= 12 and p2 <= 12:
            # Ambiguous date! (e.g. 03/09/2026 or 9/3/26)
            is_ambiguous = (p1 != p2)
            warning: Optional[str] = None

            if date_order == "MDY":
                m, d = p1, p2
                if is_ambiguous:
                    country_label = "US" if (not vendor_country or vendor_country in ["United States", "US", "USA"]) else vendor_country
                    warning = f"Date {text} read as month-first ({country_label} vendor)."
            else:
                # Default is DMY
                d, m = p1, p2
                if is_ambiguous:
                    if vendor_country:
                        country_label = "UK" if vendor_country in ["United Kingdom", "UK"] else vendor_country
                        warning = f"Date {text} read as day-first ({country_label} vendor)."
                    else:
                        warning = (
                            f"Date {text} read as day-first (default international policy for unknown vendor)."
                        )

            try:
                return date(y, m, d).isoformat(), warning
            except ValueError:
                return None, None

    # Case 3: 2-digit year prefix: YY.MM.DD or YY/MM/DD
    m_yy = re.match(r"^(\d{2})[./-](\d{1,2})[./-](\d{1,2})$", text)
    if m_yy:
        y = expand_year(int(m_yy.group(1)))
        m = int(m_yy.group(2))
        d = int(m_yy.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            try:
                return date(y, m, d).isoformat(), None
            except ValueError:
                return None, None

    return None, None


def parse_flexible_date(
    raw_str: str, vendor_country: Optional[str] = None, date_order: str = "DMY"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse any candidate date string, trying textual months first, then numeric formats.

    Returns:
        (iso_date_string or None, warning or None)
    """
    if not raw_str or not raw_str.strip():
        return None, None

    cleaned = raw_str.strip()

    # Check textual month format
    textual = parse_textual_month_date(cleaned)
    if textual:
        return textual, None

    # Check numeric formats
    return parse_numeric_date(cleaned, vendor_country=vendor_country, date_order=date_order)
