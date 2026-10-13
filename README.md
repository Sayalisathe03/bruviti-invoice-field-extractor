# Bruviti Campus Drive 2026 — Use Case 3: Invoice Field Extraction

A high-performance, deterministic, local/offline document extraction service built with **Python 3.11+** and **FastAPI**. It extracts eight normalized header fields, heuristic confidence scores, and processing warnings from digital PDF invoices with an extractable text layer.

---

## 1. Quick Start

### Prerequisites
- Python 3.11 or higher (developed and tested on Python 3.14).
- No external model weights, GPUs, or network connections are required at runtime.

### One-Command Setup and Run

Clone the repository and run the following single command from the project root:

```bash
# On Linux / macOS / Git Bash:
pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000

# On Windows PowerShell:
pip install -r requirements.txt; uvicorn app.main:app --host 127.0.0.1 --port 8000

# Or run with the included one-click launcher:
.\run.ps1        # In PowerShell
run.bat          # In Command Prompt or by double-clicking run.bat in File Explorer
```

The application will start listening on port `8000`.

- **Web UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Probe:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 2. Health Check

Verify the service is running and ready:

```bash
curl http://127.0.0.1:8000/health
```

**Expected response (HTTP 200):**
```json
{"status":"ok"}
```

---

## 3. Extracting an Invoice (API)

Submit a digital PDF invoice via multipart form-data under the exact required key `file`:

```bash
curl -F "file=@tests/fixtures/northwind_standard.pdf" http://127.0.0.1:8000/extract
```

### Response Example

```json
{
  "vendor": "Northwind Traders",
  "invoice_number": "NW-1042",
  "invoice_date": "2026-09-03",
  "due_date": "2026-10-03",
  "currency": "GBP",
  "subtotal": 361.60,
  "tax": 72.32,
  "total": 433.92,
  "confidence": {
    "vendor": 0.98,
    "invoice_number": 0.95,
    "invoice_date": 0.88,
    "due_date": 0.95,
    "currency": 0.95,
    "subtotal": 0.98,
    "tax": 0.98,
    "total": 0.98
  },
  "warnings": [
    "Date 03/09/2026 read as day-first (UK vendor)."
  ]
}
```

---

## 4. Single-Page Web UI

Navigate to [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

- **Drag & Drop / File Selector:** Select any PDF invoice.
- **Extract Invoice Button:** Submits the PDF asynchronously to `/extract`.
- **Card & Grid View:** Displays the 8 normalized fields alongside their per-field heuristic confidence bars and any document warnings.
- **Raw JSON Viewer:** Renders formatted, copyable JSON.
- **Offline Self-Contained Design:** Built with pure HTML/CSS/JavaScript with zero external CDN dependencies (fonts, styles, or libraries). Works with network disabled.

---

## 5. Running the Test Suite

Run the full offline test suite:

```bash
pytest
```

To run with verbose output and request latency measurement:

```bash
pytest -s -v
```

All 46 automated test cases execute locally in approximately 1 to 2 seconds with zero external network access.

---

## 6. Architecture & Implementation Highlights

- **Pure Local / CPU Deterministic Parser:** Utilizes PyMuPDF (`fitz`) and `pypdf` for sub-60ms in-memory PDF text extraction. Completely free of LLM calls, GPU overhead, or external API endpoints.
- **Canonical Vendors (Appendix M):**
  - Canonical resolution across all six required vendors: *Northwind Traders*, *Blue Harbour Logistics*, *Kestrel Components*, *Meridian Industrial*, *Sakura Precision*, and *Pinecrest Packaging*.
  - Suffix stripping (`Ltd`, `Inc`, `GmbH`, `KK`, `Pvt Ltd`, etc.), UK/US spelling normalization (*Harbour* vs *Harbor*), and conservative fuzzy matching. Unrecognized vendors normalize to `"unknown"`.
- **Locale-Aware Date Parsing:**
  - Day-first (DMY) default for UK, Germany, Japan, India, and unknown vendors.
  - Month-first (MDY) for US vendors.
  - Explicit warnings when ambiguous dates (e.g. `9/3/26` or `03/09/2026`) are resolved.
- **Business Rules Implemented:**
  - **O1 (Payment Terms):** Derives due dates from terms such as `Net 30`. If both a printed due date and terms are present but disagree, the printed due date is preserved with an informative warning.
  - **O2 (Arithmetic Check):** Checks `subtotal + tax == total` within 0.01 tolerance using exact `Decimal` arithmetic. On mismatch, printed values are strictly preserved and a warning is raised.
  - **O3 (Missing Currency Marker):** Infers default currency for known vendors with lower confidence (0.60) and a warning. Unknown vendors return `null` currency.
  - **O4 (Non-Invoice Exception):** Detects quotations, delivery notes, and account statements. Returns `null` for all business fields except `vendor`, accompanied by a document-type warning.
  - **O5 (JPY Precision):** Normalizes Japanese Yen whole amounts to two-decimal float precision (e.g. `150000.00`).

---

## 7. Known Limitations

1. **Scanned / Image PDFs:** Does not perform optical character recognition (OCR); scanned PDFs without an embedded digital text layer return HTTP 422 with a clear explanatory error.
2. **Heuristic Confidence Scores:** Confidence values reflect parse evidence quality, label specificity, and arithmetic consistency; they are heuristic scores in `[0.0, 1.0]`, not statistically calibrated Bayesian probabilities.
3. **Complex Multi-Page Dispersed Tables:** Designed for standard digital invoice header and summary blocks. Non-standard multi-page invoices with header fields distributed across annexes may receive lower confidence or require human review.
