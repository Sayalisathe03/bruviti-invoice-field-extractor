"""Safe in-memory PDF text extraction using PyMuPDF with pypdf fallback."""

import io
from typing import List, Tuple
import pymupdf
import pypdf


class PDFExtractionError(Exception):
    """Base exception for PDF extraction issues."""
    pass


class InvalidPDFError(PDFExtractionError):
    """Raised when file is not a valid PDF or is empty."""
    pass


class CorruptPDFError(PDFExtractionError):
    """Raised when PDF structure is corrupt or unreadable."""
    pass


class NoExtractableTextError(PDFExtractionError):
    """Raised when PDF has no extractable digital text layer (e.g. scanned image)."""
    pass


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[str, List[str]]:
    """
    Safely extract full text and individual lines from PDF bytes.

    Returns:
        (full_text, list_of_non_empty_lines)

    Raises:
        InvalidPDFError, CorruptPDFError, NoExtractableTextError
    """
    if not pdf_bytes or len(pdf_bytes) == 0:
        raise InvalidPDFError("Uploaded file is empty.")

    # Check PDF magic header
    if not pdf_bytes.startswith(b"%PDF-"):
        # Look for %PDF- in the first 1024 bytes (some PDFs have leading BOM/whitespace)
        if b"%PDF-" not in pdf_bytes[:1024]:
            raise InvalidPDFError("File does not appear to be a valid PDF document.")

    full_text = ""
    lines: List[str] = []

    # Attempt primary extraction with PyMuPDF
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            raise CorruptPDFError("PDF contains no pages.")

        page_texts: List[str] = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            if text:
                page_texts.append(text)

        doc.close()
        full_text = "\n".join(page_texts).strip()

    except pymupdf.FileDataError as e:
        raise CorruptPDFError(f"Corrupt or malformed PDF file: {str(e)}")
    except Exception:
        # Fallback to pypdf
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            if len(reader.pages) == 0:
                raise CorruptPDFError("PDF contains no pages.")

            page_texts = []
            for p in reader.pages:
                t = p.extract_text()
                if t:
                    page_texts.append(t)
            full_text = "\n".join(page_texts).strip()
        except Exception as e_pypdf:
            raise CorruptPDFError(f"Failed to read PDF document: {str(e_pypdf)}")

    # Check if text layer is present
    if not full_text or len(full_text.strip()) < 5:
        raise NoExtractableTextError("PDF contains no extractable text layer.")

    # Extract non-empty lines
    for ln in full_text.splitlines():
        cleaned_ln = ln.strip()
        if cleaned_ln:
            lines.append(cleaned_ln)

    if not lines:
        raise NoExtractableTextError("PDF contains no extractable text layer.")

    return full_text, lines
