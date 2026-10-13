"""Unit tests for canonical vendor matching, alias resolution, and unknown vendor handling."""

from app.vendors import identify_vendor


def test_canonical_vendors_exact_and_suffix_matching():
    """All six canonical vendors match with suffixes, case, and punctuation."""
    cases = [
        ("Northwind Traders Ltd", "Northwind Traders", "United Kingdom"),
        ("BLUE HARBOUR LOGISTICS", "Blue Harbour Logistics", "United Kingdom"),
        ("Kestrel Components, Inc.", "Kestrel Components", "United States"),
        ("Meridian Industrial GmbH", "Meridian Industrial", "Germany"),
        ("Sakura Precision KK", "Sakura Precision", "Japan"),
        ("Pinecrest Packaging Pvt. Ltd.", "Pinecrest Packaging", "India"),
    ]

    for raw_name, expected_canonical, expected_country in cases:
        v_name, v_info, conf, warn = identify_vendor(raw_name)
        assert v_name == expected_canonical, f"Failed for {raw_name}"
        assert v_info is not None
        assert v_info.country == expected_country
        assert conf >= 0.90
        assert warn is None


def test_spelling_variants():
    """US/UK spelling variations like Harbour/Harbor map correctly."""
    v_name, v_info, conf, warn = identify_vendor("Blue Harbor Logistics Inc")
    assert v_name == "Blue Harbour Logistics"
    assert v_info is not None
    assert v_info.default_currency == "GBP"
    assert conf >= 0.90
    assert warn is None


def test_minor_typos_and_fuzzy_matching():
    """Minor typos match canonical vendor conservatively."""
    # Slight typo "Kestral Components"
    v_name, v_info, conf, warn = identify_vendor("Kestral Components")
    assert v_name == "Kestrel Components"
    assert conf >= 0.80


def test_unrelated_vendors_remain_unknown():
    """Unrelated vendors must not map to canonical vendors."""
    unrelated = [
        "Acme Logistics International",
        "Pacific Traders Co.",
        "Zenith Global Services",
        "Apex Industrial Systems",
        "Global Precision Works",
    ]

    for raw in unrelated:
        v_name, v_info, conf, warn = identify_vendor(raw)
        assert v_name == "unknown", f"Unrelated vendor '{raw}' falsely matched to '{v_name}'"
        assert v_info is None
        assert conf <= 0.25
        assert warn == "Vendor name not in the canonical list."
