"""Generate synthetic test invoice PDFs and ground-truth fixtures using ReportLab."""

import json
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def create_pdf(filename: str, story: list):
    """Helper to generate a PDF file."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = FIXTURES_DIR / filename
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    doc.build(story)
    return filepath


def generate_all_fixtures():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
    )
    bold_style = ParagraphStyle(
        "BoldText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        fontName="Helvetica-Bold",
    )
    normal_style = ParagraphStyle(
        "NormalText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )

    # 1. Northwind Standard (UK, GBP, Net 30, DMY)
    story1 = [
        Paragraph("Northwind Traders Ltd", title_style),
        Paragraph("124 Docklands Road, London, UK | VAT: GB987654321", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>TAX INVOICE</b>", styles["Heading2"]),
        Spacer(1, 10),
        Table([
            [Paragraph("<b>Invoice Number:</b> NW-1042", normal_style), Paragraph("<b>Invoice Date:</b> 03/09/2026", normal_style)],
            [Paragraph("<b>Payment Terms:</b> Net 30", normal_style), Paragraph("<b>Due Date:</b> 03/10/2026", normal_style)],
        ], colWidths=[250, 250]),
        Spacer(1, 15),
        Table([
            ["Item Description", "Qty", "Unit Price", "Amount"],
            ["Industrial Sealant Pack", "2", "£100.00", "£200.00"],
            ["Heavy-duty Fasteners", "1", "£161.60", "£161.60"],
        ], colWidths=[260, 60, 90, 90], style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]),
        Spacer(1, 15),
        Table([
            ["Subtotal:", "£361.60"],
            ["VAT (20%):", "£72.32"],
            ["Total Due:", "£433.92"],
        ], colWidths=[400, 100], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('LINEABOVE', (0, 2), (-1, 2), 1, colors.HexColor("#1e293b")),
        ]),
    ]
    create_pdf("northwind_standard.pdf", story1)

    # 2. Kestrel Components (US, USD, MDY date 9/3/26, Net 30 with conflicting printed due date)
    story2 = [
        Paragraph("Kestrel Components, Inc.", title_style),
        Paragraph("742 Evergreen Terrace, Seattle, WA, USA", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>INVOICE</b>", styles["Heading2"]),
        Spacer(1, 10),
        Table([
            [Paragraph("<b>Invoice #:</b> KC-9921", normal_style), Paragraph("<b>Invoice Date:</b> 9/3/26", normal_style)],
            [Paragraph("<b>Terms:</b> Net 30", normal_style), Paragraph("<b>Due Date:</b> 10/15/2026", normal_style)],
        ], colWidths=[250, 250]),
        Spacer(1, 15),
        Table([
            ["Description", "Amount ($)"],
            ["Precision Machined Brackets", "$1,250.00"],
        ], colWidths=[380, 120], style=[
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]),
        Spacer(1, 15),
        Table([
            ["Subtotal:", "$1,250.00"],
            ["Sales Tax:", "$100.00"],
            ["Total Due:", "$1,350.00"],
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]),
    ]
    create_pdf("kestrel_components_mdy.pdf", story2)

    # 3. Blue Harbour Logistics (US spelling alias: Blue Harbor, derived due date from Net 30)
    story3 = [
        Paragraph("Blue Harbor Logistics", title_style),
        Paragraph("Quayside Warehouse 4, Liverpool, UK", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>Commercial Invoice</b>", styles["Heading2"]),
        Spacer(1, 10),
        Paragraph("<b>Invoice No:</b> BHL-8820", normal_style),
        Paragraph("<b>Invoice Date:</b> 14/05/2026", normal_style),
        Paragraph("<b>Payment Terms:</b> Net 30 days", normal_style),
        Spacer(1, 15),
        Table([
            ["Subtotal:", "GBP 500.00"],
            ["Tax Amount:", "GBP 100.00"],
            ["Amount Due:", "GBP 600.00"],
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]),
    ]
    create_pdf("blue_harbour_derived_due.pdf", story3)

    # 4. Meridian Industrial (Germany, EUR, dot date format, MWST)
    story4 = [
        Paragraph("Meridian Industrial GmbH", title_style),
        Paragraph("Industriestrasse 45, Stuttgart, Germany", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>Rechnung / Tax Invoice</b>", styles["Heading2"]),
        Spacer(1, 10),
        Table([
            [Paragraph("<b>Invoice Number:</b> MI-2026-44", normal_style), Paragraph("<b>Invoice Date:</b> 03.09.2026", normal_style)],
            [Paragraph("<b>Due Date:</b> 03.10.2026", normal_style), Paragraph("<b>Currency:</b> EUR", normal_style)],
        ], colWidths=[250, 250]),
        Spacer(1, 15),
        Table([
            ["Net Amount:", "1.200,50 €"],
            ["MWST (19%):", "228,10 €"],
            ["Grand Total:", "1.428,60 €"],
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]),
    ]
    create_pdf("meridian_industrial_german.pdf", story4)

    # 5. Sakura Precision (Japan, JPY, whole yen amounts without decimals)
    story5 = [
        Paragraph("Sakura Precision KK", title_style),
        Paragraph("Shinagawa Business Park, Tokyo, Japan", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>INVOICE</b>", styles["Heading2"]),
        Spacer(1, 10),
        Table([
            [Paragraph("<b>Invoice No:</b> SP-7712", normal_style), Paragraph("<b>Invoice Date:</b> 2026-04-10", normal_style)],
            [Paragraph("<b>Due Date:</b> 2026-05-10", normal_style), Paragraph("<b>Terms:</b> Net 30", normal_style)],
        ], colWidths=[250, 250]),
        Spacer(1, 15),
        Table([
            ["Subtotal:", "¥150000"],
            ["Consumption Tax (10%):", "¥15000"],
            ["Total Due:", "¥165000"],
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]),
    ]
    create_pdf("sakura_precision_jpy.pdf", story5)

    # 6. Pinecrest Packaging (India, INR, GST breakdown, Rs.)
    story6 = [
        Paragraph("Pinecrest Packaging Pvt Ltd", title_style),
        Paragraph("Sector 18, Udyog Vihar, Gurugram, India | GSTIN: 07AAAAA0000A1Z5", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>TAX INVOICE</b>", styles["Heading2"]),
        Spacer(1, 10),
        Table([
            [Paragraph("<b>Invoice No:</b> PP-IN-5501", normal_style), Paragraph("<b>Invoice Date:</b> 25/08/2026", normal_style)],
            [Paragraph("<b>Due Date:</b> 24/09/2026", normal_style), Paragraph("<b>Terms:</b> Net 30", normal_style)],
        ], colWidths=[250, 250]),
        Spacer(1, 15),
        Table([
            ["Base Amount:", "Rs. 24,500.00"],
            ["GST Amount:", "Rs. 4,410.00"],
            ["Total Amount:", "Rs. 28,910.00"],
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]),
    ]
    create_pdf("pinecrest_packaging_inr.pdf", story6)

    # 7. Arithmetic Mismatch Invoice
    story7 = [
        Paragraph("Northwind Traders", title_style),
        Paragraph("London, UK", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>Invoice No:</b> NW-BAD-01", normal_style),
        Paragraph("<b>Invoice Date:</b> 2026-08-01", normal_style),
        Paragraph("<b>Due Date:</b> 2026-08-31", normal_style),
        Spacer(1, 15),
        Table([
            ["Subtotal:", "£100.00"],
            ["Tax Amount:", "£20.00"],
            ["Total Due:", "£150.00"],  # Notice 100 + 20 != 150
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]),
    ]
    create_pdf("arithmetic_mismatch.pdf", story7)

    # 8. Missing currency marker (Meridian Industrial)
    story8 = [
        Paragraph("Meridian Industrial", title_style),
        Spacer(1, 15),
        Paragraph("<b>Invoice No:</b> MI-NOCURR-01", normal_style),
        Paragraph("<b>Invoice Date:</b> 2026-07-01", normal_style),
        Paragraph("<b>Due Date:</b> 2026-07-31", normal_style),
        Spacer(1, 15),
        Table([
            ["Subtotal:", "500.00"],
            ["Tax Amount:", "95.00"],
            ["Total Due:", "595.00"],
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]),
    ]
    create_pdf("missing_currency_meridian.pdf", story8)

    # 9. Non-invoice: Quotation
    story9 = [
        Paragraph("Kestrel Components", title_style),
        Spacer(1, 10),
        Paragraph("<b>PRICE QUOTATION</b>", styles["Heading1"]),
        Paragraph("Quote Reference: Q-8831", normal_style),
        Paragraph("Date: 2026-09-01", normal_style),
        Spacer(1, 15),
        Paragraph("This is a formal price quote, valid for 30 days. Not a tax invoice.", subtitle_style),
        Spacer(1, 15),
        Table([
            ["Subtotal:", "$1,000.00"],
            ["Estimated Tax:", "$80.00"],
            ["Estimated Total:", "$1,080.00"],
        ], colWidths=[380, 120]),
    ]
    create_pdf("non_invoice_quotation.pdf", story9)

    # 10. Non-invoice: Delivery Note
    story10 = [
        Paragraph("Blue Harbour Logistics", title_style),
        Spacer(1, 10),
        Paragraph("<b>DELIVERY NOTE</b>", styles["Heading1"]),
        Paragraph("Delivery Note Number: DN-5510", normal_style),
        Paragraph("Dispatched Date: 2026-06-12", normal_style),
        Spacer(1, 15),
        Paragraph("Goods received in good condition. Signature required.", subtitle_style),
    ]
    create_pdf("non_invoice_delivery_note.pdf", story10)

    # 11. Non-invoice: Statement of Account
    story11 = [
        Paragraph("Pinecrest Packaging", title_style),
        Spacer(1, 10),
        Paragraph("<b>STATEMENT OF ACCOUNT</b>", styles["Heading1"]),
        Paragraph("Account Number: ACC-9011", normal_style),
        Paragraph("Statement Period: August 2026", normal_style),
        Spacer(1, 15),
        Paragraph("Summary of outstanding balance as of 31-Aug-2026.", subtitle_style),
    ]
    create_pdf("non_invoice_statement.pdf", story11)

    # 12. Appendix N Example 2: kestrel_0311.pdf
    story12 = [
        Paragraph("Kestrel Components Inc. | 880 Industrial Pkwy, Dayton OH 45402, USA", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>Reference #</b> KC-0311 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Dated</b> 9/3/26", normal_style),
        Paragraph("<b>Terms</b> Net 30", normal_style),
        Paragraph("<b>Sold to</b> Bruviti Services Pvt Ltd", normal_style),
        Spacer(1, 15),
        Table([
            ["Particulars", "Total"],
            ["Bearing kit 6204-2RS (x10)", "145.00"],
            ["Drive belt A-42 (x4)", "62.80"],
            ["Shipping", "18.00"],
        ], colWidths=[380, 120], style=[
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]),
        Spacer(1, 15),
        Table([
            ["Sub total", "225.80"],
            ["Sales tax 7.25%", "16.37"],
            ["Balance Due", "$ 242.17"],
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]),
    ]
    create_pdf("kestrel_0311.pdf", story12)

    # 13. Example 3: unknown_vendor.pdf
    story13 = [
        Paragraph("Apex Global Industrial Supplies", title_style),
        Paragraph("45 Port Road, Mumbai, India", subtitle_style),
        Spacer(1, 15),
        Paragraph("<b>Invoice Number:</b> 7781", normal_style),
        Paragraph("<b>Invoice Date:</b> 2026-08-21", normal_style),
        Spacer(1, 15),
        Table([
            ["Subtotal:", "INR 12000.00"],
            ["Tax:", "INR 2160.00"],
            ["Total:", "INR 14160.00"],
        ], colWidths=[380, 120], style=[
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]),
    ]
    create_pdf("unknown_vendor.pdf", story13)

    print("All synthetic test fixtures successfully generated in", FIXTURES_DIR)


if __name__ == "__main__":
    generate_all_fixtures()
