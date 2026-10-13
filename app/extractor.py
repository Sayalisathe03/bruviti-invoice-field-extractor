"""Core extraction orchestration, label candidate parsing, business rules O1-O5, and confidence scoring."""

import re
from typing import Dict, List, Optional, Tuple

from app.amounts import (
    detect_currency_in_text,
    parse_monetary_amount,
    validate_arithmetic,
)
from app.dates import (
    derive_due_date_from_terms,
    extract_payment_terms,
    parse_flexible_date,
)
from app.schemas import ConfidenceScores, ExtractionResponse
from app.vendors import VendorInfo, identify_vendor

# Document classification patterns (Rule O4)
NON_INVOICE_PATTERNS = {
    "quotation": re.compile(
        r"\b(?:quotation|quote|price\s+quote|proforma\s+invoice|estimate)\b",
        flags=re.IGNORECASE,
    ),
    "delivery note": re.compile(
        r"\b(?:delivery\s+note|packing\s+slip|goods\s+receipt|dispatch\s+note)\b",
        flags=re.IGNORECASE,
    ),
    "statement of account": re.compile(
        r"\b(?:statement\s+of\s+account|account\s+statement|monthly\s+statement)\b",
        flags=re.IGNORECASE,
    ),
    "purchase order": re.compile(
        r"\b(?:purchase\s+order)\b",
        flags=re.IGNORECASE,
    ),
}

# Invoice labels (ranked by specificity)
INVOICE_NUM_LABELS = [
    r"invoice\s+(?:number|no|#|num|code|id|ref)",
    r"invoice\s*[:#]\s*[A-Za-z0-9]",
    r"tax\s+invoice\s+(?:number|no|#)",
    r"inv\s+(?:number|no|#|num|id|code)",
    r"bill\s+(?:number|no|#|num|id|code)",
    r"document\s+(?:number|no|#)",
    r"doc\s+(?:number|no|#)",
    r"reference\s+(?:no|#|number)",
    r"ref\s+(?:no|#)",
]

INVOICE_DATE_LABELS = [
    r"invoice\s+date",
    r"date\s+of\s+issue",
    r"issue\s+date",
    r"issued\s+on",
    r"billing\s+date",
    r"bill\s+date",
    r"tax\s+point\s+date",
    r"tax\s+point",
    r"invoice\s+dt",
    r"invoice\s+dte",
    r"dated",
    r"date",
]

DUE_DATE_LABELS = [
    r"payment\s+due\s+date",
    r"payment\s+due",
    r"due\s+date",
    r"due\s+on",
    r"due\s+by",
    r"pay\s+by",
    r"pay\s+before",
    r"payment\s+deadline",
    r"payment\s+by",
    r"due",
]

SUBTOTAL_LABELS = [
    r"amount\s+before\s+tax",
    r"total\s+before\s+tax",
    r"pre-?tax\s+(?:total|amount)",
    r"sub[\s-]?total",
    r"net\s+amount",
    r"net\s+total",
    r"net\s+sum",
    r"base\s+amount",
    r"taxable\s+amount",
]

TAX_LABELS = [
    r"total\s+tax",
    r"tax\s+total",
    r"tax\s+amount",
    r"sales\s+tax",
    r"vat\s+amount",
    r"vat\s+total",
    r"gst\s+amount",
    r"gst\s+total",
    r"consumption\s+tax",
    r"mwst",
    r"ust",
    r"umsatzsteuer",
    r"igst",
    r"cgst",
    r"sgst",
    r"vat",
    r"gst",
    r"tax",
]

TOTAL_LABELS = [
    r"total\s+due",
    r"amount\s+due",
    r"balance\s+due",
    r"grand\s+total",
    r"invoice\s+total",
    r"amount\s+payable",
    r"payable\s+amount",
    r"total\s+payable",
    r"gross\s+total",
    r"net\s+payable",
    r"total\s+amount",
    r"final\s+amount",
    r"sum\s+total",
    r"total",
]


def classify_document(lines: List[str]) -> Optional[str]:
    """
    Check if the document is a non-invoice (quotation, delivery note, statement, etc.).
    Examines top 15 lines and document title/heading.
    """
    header_sample = " \n ".join(lines[:15]).lower()

    # Rule out normal invoices first
    has_invoice_keyword = bool(re.search(r"\b(?:tax\s+invoice|invoice)\b", header_sample))

    for doc_type, pattern in NON_INVOICE_PATTERNS.items():
        # Check if prominent in the first few lines
        for ln in lines[:8]:
            ln_lower = ln.lower().strip()
            # If line is essentially just the title (e.g. "QUOTATION" or "DELIVERY NOTE")
            if pattern.search(ln_lower):
                # If it's a statement, ensure it's not merely boilerplate
                if doc_type == "statement of account":
                    if any(s in ln_lower for s in ["statement of account", "account statement", "monthly statement"]):
                        return doc_type
                elif not has_invoice_keyword or len(ln_lower) < 40:
                    return doc_type

    return None


def extract_labeled_text(
    lines: List[str],
    labels: List[str],
    exclude_labels: Optional[List[str]] = None,
) -> List[Tuple[str, int]]:
    """
    Search for lines matching any label regex, extracting the remaining text on the same line
    or on the immediate following line.

    Returns:
        List of (candidate_string, priority_index)
    """
    candidates: List[Tuple[str, int]] = []

    for priority, label_pat in enumerate(labels):
        full_regex = re.compile(rf"\b({label_pat})(?:\b|(?=[^a-zA-Z0-9]))\s*[:#-]?\s*(.*)$", flags=re.IGNORECASE)

        for idx, line in enumerate(lines):
            line_clean = line.strip()

            # Check if this line is excluded (e.g. avoiding "Due Date" when searching for "Date")
            if exclude_labels:
                skip = False
                for ex_pat in exclude_labels:
                    if re.search(rf"\b({ex_pat})(?:\b|(?=[^a-zA-Z0-9]))", line_clean, flags=re.IGNORECASE):
                        skip = True
                        break
                if skip:
                    continue

            m = full_regex.search(line_clean)
            if m:
                val = m.group(2).strip()
                if val:
                    candidates.append((val, priority))
                    # If val only contained a rate/annotation like (20%): or colon with no monetary digits,
                    # the actual amount is on the next line
                    val_without_rate = re.sub(r"\(?\s*\d+(?:\.\d+)?\s*%\s*\)?", "", val).strip(" :#-")
                    if not any(ch.isdigit() for ch in val_without_rate) and idx + 1 < len(lines):
                        next_line = lines[idx + 1].strip()
                        if next_line:
                            candidates.append((next_line, priority + 1))
                elif idx + 1 < len(lines):
                    # Value is on the next line
                    next_line = lines[idx + 1].strip()
                    if next_line:
                        candidates.append((next_line, priority + 1))

    return candidates


def extract_invoice_number(lines: List[str]) -> Tuple[Optional[str], float]:
    """Extract preserved invoice number identifier."""
    candidates = extract_labeled_text(lines, INVOICE_NUM_LABELS)

    for cand_text, priority in candidates:
        # Clean candidates
        # Take the first token or string before spaces/commas if multiple fields are on the same line
        # e.g., "NW-1042 Date: 2026-09-03" -> "NW-1042"
        tokens = cand_text.split()
        if not tokens:
            continue
        first_token = tokens[0].strip().rstrip(",;:")

        # Validate: not a date, not an amount, not purely words
        if re.match(r"^\d{4}[./-]\d{1,2}[./-]\d{1,2}$", first_token):
            continue
        if re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$", first_token):
            continue
        if re.match(r"^[$£€¥₹]", first_token):
            continue
        if re.match(r"^\d+\.\d{2}$", first_token):
            continue
        if first_token.lower() in ["date", "tax", "total", "subtotal", "due", "net", "terms"]:
            continue

        # Check if well-formed (has digits or letters with length >= 2)
        if len(first_token) >= 2 and any(ch.isalnum() for ch in first_token):
            confidence = 0.95 if priority <= 3 else 0.85
            return first_token, confidence

    return None, 0.0


def extract_date_field(
    lines: List[str],
    labels: List[str],
    exclude_labels: Optional[List[str]],
    vendor_country: Optional[str],
    date_order: str,
) -> Tuple[Optional[str], float, Optional[str]]:
    """
    Extract and parse date field candidate.

    Returns:
        (iso_date_or_none, confidence, ambiguity_warning_or_none)
    """
    candidates = extract_labeled_text(lines, labels, exclude_labels=exclude_labels)

    for cand_text, priority in candidates:
        # Try full candidate text or first date-like segment
        # First test whole string
        iso_dt, warn = parse_flexible_date(cand_text, vendor_country, date_order)
        if iso_dt:
            conf = 0.95 if not warn else 0.88
            if priority > 3:
                conf = max(0.50, conf - 0.10)
            return iso_dt, conf, warn

        # Check sub-segments in cand_text (e.g. "03/09/2026 PO# 1234")
        words = cand_text.split()
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                chunk = " ".join(words[i:j])
                iso_dt, warn = parse_flexible_date(chunk, vendor_country, date_order)
                if iso_dt:
                    conf = 0.92 if not warn else 0.85
                    if priority > 3:
                        conf = max(0.50, conf - 0.10)
                    return iso_dt, conf, warn

    return None, 0.0, None


def extract_amount_field(
    lines: List[str],
    labels: List[str],
    exclude_labels: Optional[List[str]] = None,
) -> Tuple[Optional[float], float]:
    """
    Extract and parse monetary amount field.

    Returns:
        (amount_or_none, confidence)
    """
    candidates = extract_labeled_text(lines, labels, exclude_labels=exclude_labels)

    for cand_text, priority in candidates:
        amount = parse_monetary_amount(cand_text)
        if amount is not None:
            conf = 0.96 if priority <= 2 else 0.88
            return amount, conf

    return None, 0.0


def extract_currency(
    full_text: str, lines: List[str], vendor_info: Optional[VendorInfo]
) -> Tuple[Optional[str], float, Optional[str]]:
    """
    Identify currency from document text or infer from vendor default (Rule O3).

    Returns:
        (currency_or_none, confidence, warning_or_none)
    """
    # 1. Search in lines with amounts or total
    for ln in lines:
        if any(kw in ln.lower() for kw in ["total", "due", "subtotal", "tax", "balance", "amount"]):
            curr = detect_currency_in_text(ln)
            if curr:
                return curr, 0.95, None

    # 2. Search entire document for explicit currency
    curr = detect_currency_in_text(full_text)
    if curr:
        return curr, 0.93, None

    # 3. Rule O3: Missing currency marker
    if vendor_info:
        inferred = vendor_info.default_currency
        return inferred, 0.60, f"Currency inferred from vendor default ({inferred})."

    # 4. Unknown vendor with no currency marker
    return None, 0.0, "No currency detected for unknown vendor."


def extract_invoice(full_text: str, lines: List[str]) -> ExtractionResponse:
    """
    Main extraction function for a single document.
    Executes layered, explainable parsing across all eight header fields.
    """
    warnings: List[str] = []

    # Step 1: Identify Vendor first (needed for document classification & context)
    vendor_name, vendor_info, vendor_conf, vendor_warn = identify_vendor(full_text, lines)
    if vendor_warn:
        warnings.append(vendor_warn)

    vendor_country = vendor_info.country if vendor_info else None
    vendor_date_order = vendor_info.date_order if vendor_info else "DMY"

    # Step 2: Document Classification (Rule O4)
    doc_type = classify_document(lines)
    if doc_type:
        warnings.append(f"Document detected as {doc_type} (not an invoice).")
        return ExtractionResponse(
            vendor=vendor_name,
            invoice_number=None,
            invoice_date=None,
            due_date=None,
            currency=None,
            subtotal=None,
            tax=None,
            total=None,
            confidence=ConfidenceScores(
                vendor=round(vendor_conf, 2),
                invoice_number=0.0,
                invoice_date=0.0,
                due_date=0.0,
                currency=0.0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
            ),
            warnings=warnings,
        )

    # Step 3: Extract Invoice Number
    inv_num, inv_num_conf = extract_invoice_number(lines)
    if not inv_num:
        warnings.append("Invoice number not found.")

    # Step 4: Extract Invoice Date
    inv_date, inv_date_conf, inv_date_warn = extract_date_field(
        lines=lines,
        labels=INVOICE_DATE_LABELS,
        exclude_labels=DUE_DATE_LABELS,
        vendor_country=vendor_country,
        date_order=vendor_date_order,
    )
    if inv_date_warn:
        warnings.append(inv_date_warn)
    if not inv_date:
        warnings.append("Invoice date not found.")

    # Step 5: Extract Due Date & Payment Terms (Rule O1)
    printed_due_date, printed_due_conf, printed_due_warn = extract_date_field(
        lines=lines,
        labels=DUE_DATE_LABELS,
        exclude_labels=None,
        vendor_country=vendor_country,
        date_order=vendor_date_order,
    )
    if printed_due_warn:
        warnings.append(printed_due_warn)

    term_days, term_label = extract_payment_terms(full_text)

    due_date: Optional[str] = None
    due_date_conf = 0.0

    if printed_due_date and term_days is not None and inv_date:
        # Both printed due date and payment terms exist
        derived_from_terms = derive_due_date_from_terms(inv_date, term_days)
        if derived_from_terms and derived_from_terms != printed_due_date:
            # Disagreement: keep printed due date and add warning
            due_date = printed_due_date
            due_date_conf = 0.90
            warnings.append(
                f"Printed due date ({printed_due_date}) conflicts with payment terms {term_label}; "
                f"printed due date retained."
            )
        else:
            # Agreement or no conflict
            due_date = printed_due_date
            due_date_conf = printed_due_conf
    elif printed_due_date:
        # Printed due date only
        due_date = printed_due_date
        due_date_conf = printed_due_conf
    elif term_days is not None and inv_date:
        # No printed due date, but payment terms present: derive due date
        derived = derive_due_date_from_terms(inv_date, term_days)
        if derived:
            due_date = derived
            due_date_conf = 0.85
            warnings.append(f"Due date derived from terms {term_label}.")
        else:
            warnings.append(f"Unable to derive due date from terms {term_label}.")
    else:
        # No due date found
        warnings.append("No due date or payment terms found.")

    # Step 6: Extract Currency (Rule O3)
    currency, currency_conf, curr_warn = extract_currency(full_text, lines, vendor_info)
    if curr_warn:
        warnings.append(curr_warn)

    # Step 7: Extract Subtotal, Tax, Total Amounts
    subtotal, subtotal_conf = extract_amount_field(
        lines=lines,
        labels=SUBTOTAL_LABELS,
        exclude_labels=TAX_LABELS + [r"total\s+due", r"amount\s+due", r"grand\s+total"],
    )
    if subtotal is None:
        warnings.append("Subtotal amount not found.")

    tax, tax_conf = extract_amount_field(
        lines=lines,
        labels=TAX_LABELS,
        exclude_labels=SUBTOTAL_LABELS
        + [
            r"total\s+due",
            r"amount\s+due",
            r"grand\s+total",
            r"vat\s*(?:reg|registration|number|no|#|id|code)",
            r"gstin",
            r"vat:\s*[a-z]{2}",
        ],
    )
    if tax is None:
        # Check if tax is explicitly 0 or if items are untaxed
        warnings.append("Tax amount not found.")

    total, total_conf = extract_amount_field(
        lines=lines,
        labels=TOTAL_LABELS,
        exclude_labels=SUBTOTAL_LABELS,
    )
    if total is None:
        warnings.append("Total amount not found.")

    # Step 8: Validate Arithmetic (Rule O2)
    is_arithmetic_valid, arith_warn = validate_arithmetic(subtotal, tax, total)
    if not is_arithmetic_valid and arith_warn:
        warnings.append(arith_warn)
        # Arithmetic mismatch slightly reduces confidence of the amounts
        if subtotal_conf > 0.0:
            subtotal_conf = max(0.50, subtotal_conf - 0.12)
        if tax_conf > 0.0:
            tax_conf = max(0.50, tax_conf - 0.12)
        if total_conf > 0.0:
            total_conf = max(0.50, total_conf - 0.12)
    elif is_arithmetic_valid and subtotal is not None and tax is not None and total is not None:
        # Arithmetic matches, boost amount confidences!
        subtotal_conf = min(0.98, subtotal_conf + 0.02)
        tax_conf = min(0.98, tax_conf + 0.02)
        total_conf = min(0.98, total_conf + 0.02)

    # Step 9: Build and return validated response
    confidence_obj = ConfidenceScores(
        vendor=round(min(1.0, max(0.0, vendor_conf)), 2),
        invoice_number=round(min(1.0, max(0.0, inv_num_conf)), 2),
        invoice_date=round(min(1.0, max(0.0, inv_date_conf)), 2),
        due_date=round(min(1.0, max(0.0, due_date_conf)), 2),
        currency=round(min(1.0, max(0.0, currency_conf)), 2),
        subtotal=round(min(1.0, max(0.0, subtotal_conf)), 2),
        tax=round(min(1.0, max(0.0, tax_conf)), 2),
        total=round(min(1.0, max(0.0, total_conf)), 2),
    )

    return ExtractionResponse(
        vendor=vendor_name,
        invoice_number=inv_num,
        invoice_date=inv_date,
        due_date=due_date,
        currency=currency,
        subtotal=subtotal,
        tax=tax,
        total=total,
        confidence=confidence_obj,
        warnings=warnings,
    )
