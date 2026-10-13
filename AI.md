# AI Usage Disclosure (AI.md)

In compliance with Section 2 and Section 12 of the Bruviti Campus Drive 2026 Use Case 3 brief, this document transparently records all AI tools used throughout the development of this repository and their specific purposes.

---

## 1. AI Tools Used

| Tool Name | Developer / Provider | Primary Usage |
|---|---|---|
| **Google Antigravity / Gemini 3.8 Flash** | Google DeepMind | Requirements decomposition, architecture design, code generation, regex boundary debugging, and test fixture authoring. |

---

## 2. Specific Contributions & Tasks

### A. Requirements Decomposition & Architectural Design
- Analyzed the Master Prompt specifications, including the exact JSON schema contract, business rules O1–O5, the six canonical vendor locales, and the non-invoice document exception.
- Designed a lightweight, modular architecture separating schema models (`schemas.py`), vendor normalization (`vendors.py`), locale date parsing (`dates.py`), amount and currency parsing (`amounts.py`), PDF extraction (`pdf_reader.py`), and extraction orchestration (`extractor.py`).

### B. Implementation & Code Generation
- Generated deterministic parsing logic in pure Python without external machine learning model dependencies.
- Implemented locale-aware date ordering (DMY vs MDY) and ambiguity detection with human-readable warnings.
- Authored the self-contained single-page HTML/CSS/JavaScript reviewer UI embedded directly in `app/main.py`.
- Formatted `requirements.txt` with bounded versions and created `.gitignore` to prevent repository clutter.

### C. Synthetic Fixture Authoring & Testing
- Developed `scripts/generate_test_invoices.py` using ReportLab to programmatically generate reproducible synthetic PDF invoices for all six canonical vendors and non-invoice document types.
- Authored comprehensive test suites in `tests/` covering API endpoints (`test_extract_api.py`, `test_health_and_ui.py`), unit logic (`test_dates.py`, `test_amounts.py`, `test_vendors.py`), and business rules (`test_business_rules.py`).

### D. Debugging & Iterative Refinement
- Diagnosed regex word-boundary limitations where patterns ending in `#` (e.g. `Invoice #:`) failed when followed by non-word punctuation like colons. Refined regex boundary lookaheads to support symbols and punctuation cleanly.
- Resolved tax amount collisions with company VAT registration IDs by introducing pattern exclusions and numeric sanitization.
- Fixed European comma decimals and currency prefix handling (e.g. `Rs.`) in monetary amount parsing.

---

## 3. Candidate Review & Verification Statement

All code, schemas, and tests in this repository have been inspected, executed locally, and verified against the brief's non-negotiable requirements. The candidate can explain every architectural decision, regex pattern, and business rule implementation during review.
