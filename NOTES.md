# Engineering Notes: Bruviti Use Case 3 — Invoice Field Extraction

## 1. Key Design Choices
- **Deterministic Rule-Based Architecture:** Rather than introducing a heavyweight vision or language model that could violate latency or memory limits, the system uses a layered, explainable pipeline:
  1. *Text Layer Intake:* In-memory extraction via PyMuPDF (`fitz`) with `pypdf` fallback.
  2. *Vendor Identification & Locale Context:* Normalizes legal suffixes, punctuation, and known aliases (e.g., Harbour/Harbor) before matching canonical vendors. Country metadata directly informs date ordering (DMY vs MDY) and default currency.
  3. *Contextual & Proximity Candidate Extraction:* Searches multi-token labels and evaluates same-line and adjacent-line values to decouple extraction from fixed visual positions.
  4. *Normalization & Decimal Arithmetic:* Validates arithmetic with exact `Decimal` precision without mutating printed values.
  5. *Heuristic Confidence Scoring:* Assigns scores based on label specificity, parse quality, and arithmetic consistency.
- **Single-Process FastAPI Service:** API routes, business logic, and an offline HTML/CSS/JavaScript reviewer UI are served together on port 8000 without requiring Node.js or frontend toolchains.

## 2. Assumptions & Schema Interpretations
- **Non-Invoice Documents (Rule O4):** For quotations, delivery notes, and statements of account, all business fields are returned as `null` except `vendor` (which is extracted if present). Heuristic confidence for extracted vendor reflects match evidence; unextracted fields are set to `0.0`.
- **Unknown Vendor Date Ambiguity:** When an ambiguous numeric date (e.g. `03/09/2026`) occurs on an invoice from an unrecognized vendor, the service defaults to international standard Day-First (DMY) order and emits an explicit warning.
- **Currency Absence (Rule O3):** When no currency symbol or code is found for an unrecognized vendor, currency is returned as `null` with a warning rather than guessing.

## 3. Deliberate Scope Cuts
- **OCR Elimination:** Scanned images and handwritten documents were explicitly out of scope; the service focuses exclusively on digital PDFs with a text layer.
- **No Database or External Storage:** Extraction is stateless and in-memory; uploaded streams are discarded immediately after request processing to maximize privacy and throughput.

## 4. Measured Performance
- **Latency Benchmark:** Measured end-to-end request latency on an ordinary laptop CPU averaged **~50–60 ms per invoice** (well below the required 1,000 ms threshold).
- **Memory Footprint:** Startup memory footprint remains under 60 MB RSS.

## 5. What Would Be Improved Next
- **Layout Spatial Graphs:** Incorporating relative 2D bounding boxes (X/Y coordinates) could further disambiguate multi-column tables where line wrapping separates labels and values.
- **Multilingual Token Dictionaries:** Expanding localized tax terminology (e.g., *TVA*, *IVA*, *USt*) for broader European and Asian supplier bases.
