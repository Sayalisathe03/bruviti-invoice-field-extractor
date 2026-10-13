"""Appendix M canonical vendors metadata, alias normalization, and matching logic."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class VendorInfo:
    """Canonical vendor specification according to Appendix M."""

    canonical_name: str
    country: str
    default_currency: str
    date_order: str  # "DMY" or "MDY"
    aliases: List[str] = field(default_factory=list)


CANONICAL_VENDORS: Dict[str, VendorInfo] = {
    "Northwind Traders": VendorInfo(
        canonical_name="Northwind Traders",
        country="United Kingdom",
        default_currency="GBP",
        date_order="DMY",
        aliases=[
            "northwind traders",
            "northwind trader",
            "northwind trading",
            "northwind",
            "north wind traders",
        ],
    ),
    "Blue Harbour Logistics": VendorInfo(
        canonical_name="Blue Harbour Logistics",
        country="United Kingdom",
        default_currency="GBP",
        date_order="DMY",
        aliases=[
            "blue harbour logistics",
            "blue harbor logistics",
            "blue harbour",
            "blue harbor",
            "blue harbour logistic",
            "blue harbor logistic",
        ],
    ),
    "Kestrel Components": VendorInfo(
        canonical_name="Kestrel Components",
        country="United States",
        default_currency="USD",
        date_order="MDY",
        aliases=[
            "kestrel components",
            "kestrel component",
            "kestrel",
            "kestral components",
        ],
    ),
    "Meridian Industrial": VendorInfo(
        canonical_name="Meridian Industrial",
        country="Germany",
        default_currency="EUR",
        date_order="DMY",
        aliases=[
            "meridian industrial",
            "meridian industrie",
            "meridian industries",
            "meridian",
        ],
    ),
    "Sakura Precision": VendorInfo(
        canonical_name="Sakura Precision",
        country="Japan",
        default_currency="JPY",
        date_order="DMY",
        aliases=[
            "sakura precision",
            "sakura precisions",
            "sakura",
            "sakura seiki",
        ],
    ),
    "Pinecrest Packaging": VendorInfo(
        canonical_name="Pinecrest Packaging",
        country="India",
        default_currency="INR",
        date_order="DMY",
        aliases=[
            "pinecrest packaging",
            "pinecrest packagings",
            "pine crest packaging",
            "pinecrest pack",
            "pinecrest",
        ],
    ),
}

LEGAL_SUFFIXES = [
    r"\bpvt\.?\s*ltd\.?\b",
    r"\bprivate\s+limited\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\binc\.?\b",
    r"\bincorporated\b",
    r"\bgmbh\b",
    r"\bkk\b",
    r"\bkabushiki\s+kaisha\b",
    r"\bllc\b",
    r"\bllp\b",
    r"\bplc\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bco\.?\b",
    r"\bcompany\b",
    r"\bs\.a\.\b",
    r"\bag\b",
]

_LEGAL_SUFFIX_REGEX = re.compile("|".join(LEGAL_SUFFIXES), flags=re.IGNORECASE)


def normalize_vendor_text(text: str) -> str:
    """Normalize vendor text by lowercasing, stripping legal suffixes, punctuation, and excess spaces."""
    t = text.lower()
    # Strip legal suffixes
    t = _LEGAL_SUFFIX_REGEX.sub(" ", t)
    # Strip punctuation except spaces and letters/digits
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    # Normalize spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)

    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)

    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0[:] = v1[:]

    return v0[len(s2)]


def similarity_ratio(s1: str, s2: str) -> float:
    """Normalized similarity score in range [0.0, 1.0]."""
    if not s1 or not s2:
        return 0.0
    dist = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return 1.0 - (dist / max_len)


def identify_vendor(
    text_content: str, header_lines: Optional[List[str]] = None
) -> Tuple[str, Optional[VendorInfo], float, Optional[str]]:
    """
    Identify canonical vendor from document header or full text.

    Returns:
        (canonical_name, VendorInfo or None, confidence_score, warning_message or None)
    """
    # 1. Search in header lines first (most reliable for sender/vendor), then full text
    candidates_to_check: List[str] = []
    if header_lines:
        candidates_to_check.extend(header_lines[:15])

    # Also extract individual lines from the first 2500 characters of text_content
    preview_lines = [
        ln.strip()
        for ln in text_content[:2500].splitlines()
        if ln.strip() and len(ln.strip()) >= 3
    ][:20]
    for ln in preview_lines:
        if ln not in candidates_to_check:
            candidates_to_check.append(ln)

    # Cleaned candidates
    normalized_lines = [normalize_vendor_text(c) for c in candidates_to_check if c]

    # Step A: Exact and Alias matching
    for vendor_name, info in CANONICAL_VENDORS.items():
        norm_canonical = normalize_vendor_text(vendor_name)
        norm_aliases = [normalize_vendor_text(a) for a in info.aliases]

        # Check line exact matches
        for norm_ln in normalized_lines:
            if not norm_ln:
                continue
            # Exact line match with canonical
            if norm_ln == norm_canonical:
                return vendor_name, info, 0.98, None
            # Exact line match with alias
            if norm_ln in norm_aliases:
                return vendor_name, info, 0.95, None
            # Substring exact match (e.g. "From: Northwind Traders Ltd" -> contains "northwind traders")
            for alias in norm_aliases:
                # Require word-boundary-like containment to prevent partial word false positives
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, norm_ln):
                    # If alias is very short (e.g. single word), check it is sufficiently distinctive
                    if len(alias.split()) > 1 or len(alias) >= 6:
                        return vendor_name, info, 0.93, None

    # Step B: Also search whole header text for exact aliases
    full_preview_norm = normalize_vendor_text(text_content[:2000])
    for vendor_name, info in CANONICAL_VENDORS.items():
        for alias in info.aliases:
            pattern = r"\b" + re.escape(normalize_vendor_text(alias)) + r"\b"
            if re.search(pattern, full_preview_norm):
                if len(alias.split()) > 1 or len(alias) >= 6:
                    return vendor_name, info, 0.92, None

    # Step C: Conservative fuzzy matching
    # Look for high similarity with canonical name or main multi-word aliases
    best_match: Optional[Tuple[str, VendorInfo, float]] = None
    highest_sim = 0.0

    for vendor_name, info in CANONICAL_VENDORS.items():
        norm_canonical = normalize_vendor_text(vendor_name)
        # Check against each line candidate
        for norm_ln in normalized_lines:
            if len(norm_ln) < 4:
                continue
            # Compare similarity
            sim = similarity_ratio(norm_ln, norm_canonical)
            if sim > highest_sim:
                highest_sim = sim
                best_match = (vendor_name, info, sim)

            # Also check primary distinct alias
            for alias in info.aliases:
                norm_a = normalize_vendor_text(alias)
                sim_a = similarity_ratio(norm_ln, norm_a)
                if sim_a > highest_sim:
                    highest_sim = sim_a
                    best_match = (vendor_name, info, sim_a)

    # Conservative threshold: must be >= 0.82 to avoid unrelated vendors matching
    if best_match and highest_sim >= 0.82:
        matched_vendor, matched_info, _ = best_match
        return matched_vendor, matched_info, round(min(0.88, highest_sim), 2), None

    # Not recognized
    conf = 0.20 if normalized_lines else 0.0
    return "unknown", None, conf, "Vendor name not in the canonical list."
