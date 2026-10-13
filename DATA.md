# Synthetic Data Provenance and Evaluation Strategy

## 1. Data Provenance & Synthetic Origin

No proprietary, real supplier, or confidential customer data was used or collected for this project. All test documents and fixtures located in `tests/fixtures/` were synthetically generated using ReportLab via `scripts/generate_test_invoices.py`.

The synthetic documents were designed to test layout diversity, locale variations, label variations, and boundary conditions specified in the Bruviti Campus Drive 2026 Use Case 3 brief.

---

## 2. Generation Methodology & Variations

The fixture generator (`scripts/generate_test_invoices.py`) programmatically produces reproducible PDF invoices and non-invoice documents covering all six canonical vendors and key edge cases:

| Fixture File | Vendor Tested | Country / Locale | Tested Features & Variations |
|---|---|---|---|
| `northwind_standard.pdf` | Northwind Traders Ltd | UK (DMY, GBP) | Table layout, VAT reg in header vs monetary tax, `03/09/2026` ambiguous DMY date, `Net 30` terms. |
| `kestrel_components_mdy.pdf` | Kestrel Components, Inc. | US (MDY, USD) | US format `9/3/26`, `Invoice #: KC-9921`, conflicting printed due date vs `Net 30` terms (Rule O1). |
| `blue_harbour_derived_due.pdf` | Blue Harbor Logistics | UK (DMY, GBP) | US spelling alias (*Harbor*), no printed due date, derived due date from `Net 30 days` (Rule O1). |
| `meridian_industrial_german.pdf` | Meridian Industrial GmbH | Germany (DMY, EUR) | German dot date format `03.09.2026`, European decimal commas `1.200,50 €`, MWST tax label. |
| `sakura_precision_jpy.pdf` | Sakura Precision KK | Japan (DMY, JPY) | Japanese Yen amounts printed without decimal places (`¥150000`), Consumption Tax label (Rule O5). |
| `pinecrest_packaging_inr.pdf` | Pinecrest Packaging Pvt Ltd | India (DMY, INR) | Indian Rupee formatting (`Rs. 24,500.00`), GST breakdown, GSTIN in header. |
| `arithmetic_mismatch.pdf` | Northwind Traders | UK (DMY, GBP) | Subtotal + Tax does not match Total (`£100 + £20 != £150`), testing Rule O2 preservation. |
| `missing_currency_meridian.pdf` | Meridian Industrial | Germany (EUR) | No currency symbol or code printed, testing Rule O3 default currency inference. |
| `non_invoice_quotation.pdf` | Kestrel Components | US (USD) | Document titled "PRICE QUOTATION", testing Rule O4 null fields and warning. |
| `non_invoice_delivery_note.pdf` | Blue Harbour Logistics | UK (GBP) | Document titled "DELIVERY NOTE", testing Rule O4. |
| `non_invoice_statement.pdf` | Pinecrest Packaging | India (INR) | Document titled "STATEMENT OF ACCOUNT", testing Rule O4. |
| `kestrel_0311.pdf` | Kestrel Components, Inc. | US (MDY, USD) | Verbatim reproduction of Appendix N Example 2 (`Reference # KC-0311`, `Dated 9/3/26`, `Net 30`). |
| `unknown_vendor.pdf` | Apex Global Supplies | India (INR) | Verbatim reproduction of Example 3 (`vendor: unknown`, numeric invoice no `7781`, no terms). |

---

## 3. Offline Testing Strategy

- **Complete Network Independence:** No external network connections, LLM APIs, cloud inference, or downloads are used during tests or runtime.
- **End-to-End API Testing (`tests/test_extract_api.py`):** Posts actual generated PDF binary streams to `/extract` and validates response structure, field normalization, and performance.
- **Unit Testing:** Dedicated test files cover date parsing (`test_dates.py`), amount and currency parsing (`test_amounts.py`), vendor normalization (`test_vendors.py`), and business rules (`test_business_rules.py`).
- **Error Handling Coverage:** Verifies graceful handling of non-PDF uploads, corrupted PDF bytes, missing files, and digital PDFs lacking extractable text layers.

---

## 4. Known Limitations & Potential Failure Modes on Real Data

1. **Hidden Evaluation Invoices:** These synthetic samples cannot prove accuracy on Bruviti's hidden evaluation invoices, which contain unseen layouts and labels.
2. **Text Extraction Dependencies:** If a real invoice uses broken font encoding or non-standard Unicode mapping (ToUnicode CMap tables missing or corrupted), the extracted text layer may yield garbage characters.
3. **Complex Dispersed Tables:** Invoices where total figures are embedded inside dense narrative paragraphs rather than conventional header/summary key-value pairs may trigger lower confidence scores or require human validation.
4. **Scanned / Handwritten Documents:** Explicitly out of scope per the brief; the service requires a digital PDF text layer.
