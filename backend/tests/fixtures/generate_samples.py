"""
Generate three sample trade document PDFs for pipeline testing.

  sample_bol_approve.pdf     — Bill of Lading, all fields valid   → approve
  sample_bol_amend.pdf       — Bill of Lading, wrong HS code       → amend
  sample_invoice_review.pdf  — Commercial Invoice, consignee fuzzy → review (uncertain)

Run from backend/:
    python tests/fixtures/generate_samples.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT_DIR = Path(__file__).parent
W, H = A4
STYLES = getSampleStyleSheet()


def _doc(filename: str):
    path = OUT_DIR / filename
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )


def _heading(text: str):
    return Paragraph(f"<b>{text}</b>", STYLES["Title"])


def _subheading(text: str):
    return Paragraph(f"<b>{text}</b>", STYLES["Heading2"])


def _field_table(rows: list[tuple[str, str]]):
    data = [["Field", "Value"]] + list(rows)
    t = Table(data, colWidths=[6 * cm, 10 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b4c7e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4fa")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


# ---------------------------------------------------------------------------
# 1. sample_bol_approve.pdf  — all fields match ACME_001 rules → approve
# ---------------------------------------------------------------------------
def make_bol_approve():
    doc = _doc("sample_bol_approve.pdf")
    story = [
        _heading("BILL OF LADING"),
        Paragraph("NovaFreight Carriers — B/L No. NF-2024-00183", STYLES["Normal"]),
        Spacer(1, 0.5 * cm),
        _subheading("Shipper / Exporter"),
        _field_table([
            ("Company Name", "Shanghai Tech Solutions Co., Ltd."),
            ("Address", "88 Pudong Avenue, Shanghai, 200120, China"),
            ("Contact", "+86 21 5555 0100"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Consignee"),
        _field_table([
            ("Company Name", "Acme Imports Pvt Ltd"),
            ("Address", "42 Industrial Estate, Navi Mumbai, Maharashtra 400705, India"),
            ("GSTIN", "27AABCA1234C1ZP"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Shipment Details"),
        _field_table([
            ("Port of Loading", "CNSHA"),
            ("Port of Discharge", "INNSA"),
            ("Incoterms", "CIF"),
            ("Vessel / Voyage", "MV Ever Given  /  Voyage 042E"),
            ("Bill of Lading Date", "2024-03-15"),
            ("B/L Type", "Original — negotiable"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Cargo Description"),
        _field_table([
            ("Description of Goods", "Laptop Computers and Accessories"),
            ("HS Code", "8471.30"),
            ("Gross Weight", "1250.50 KG"),
            ("Measurement", "8.40 CBM"),
            ("Packages", "240 cartons"),
            ("Invoice Number", "INV-20240183"),
            ("Invoice Date", "2024-03-10"),
            ("Invoice Value", "USD 185,600.00"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Freight & Charges"),
        _field_table([
            ("Freight Terms", "PREPAID"),
            ("Ocean Freight", "USD 3,200.00"),
            ("Insurance", "USD 370.00"),
            ("THC — Origin", "USD 280.00"),
        ]),
        Spacer(1, 0.6 * cm),
        Paragraph(
            "Signed for the carrier NovaFreight Carriers by its authorised agent.",
            STYLES["Italic"],
        ),
    ]
    doc.build(story)
    print("Created:", OUT_DIR / "sample_bol_approve.pdf")


# ---------------------------------------------------------------------------
# 2. sample_bol_amend.pdf  — HS code 9999.99 (not in ACME allowed list) → amend
# ---------------------------------------------------------------------------
def make_bol_amend():
    doc = _doc("sample_bol_amend.pdf")
    story = [
        _heading("BILL OF LADING"),
        Paragraph("OceanLink Express — B/L No. OL-2024-00441", STYLES["Normal"]),
        Spacer(1, 0.5 * cm),
        _subheading("Shipper / Exporter"),
        _field_table([
            ("Company Name", "Guangzhou Manufacturing Group"),
            ("Address", "15 Factory Road, Guangzhou, 510620, China"),
            ("Contact", "+86 20 8888 3300"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Consignee"),
        _field_table([
            ("Company Name", "Acme Imports Pvt Ltd"),
            ("Address", "42 Industrial Estate, Navi Mumbai, Maharashtra 400705, India"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Shipment Details"),
        _field_table([
            ("Port of Loading", "CNSZX"),
            ("Port of Discharge", "INNSA"),
            ("Incoterms", "CIF"),
            ("Vessel / Voyage", "MV Pacific Eagle  /  Voyage 017W"),
            ("Bill of Lading Date", "2024-04-02"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Cargo Description"),
        _field_table([
            ("Description of Goods", "Electronic Control Units and PCB Assemblies"),
            # HS code deliberately wrong — not in ACME's allowed list
            ("HS Code", "9999.99"),
            ("Gross Weight", "320.00 KG"),
            ("Measurement", "2.10 CBM"),
            ("Packages", "85 cartons"),
            ("Invoice Number", "INV-20240441"),
            ("Invoice Value", "USD 47,250.00"),
        ]),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "<b>Note:</b> The HS code 9999.99 is a placeholder and must be corrected "
            "by the supplier before customs clearance.",
            STYLES["Normal"],
        ),
        Spacer(1, 0.6 * cm),
        Paragraph(
            "Signed for the carrier OceanLink Express by its authorised agent.",
            STYLES["Italic"],
        ),
    ]
    doc.build(story)
    print("Created:", OUT_DIR / "sample_bol_amend.pdf")


# ---------------------------------------------------------------------------
# 3. sample_invoice_review.pdf  — consignee name is an ambiguous variant → review
#    "ACME IMPORTS" (abbreviated, no Pvt Ltd) — fuzzy match will be uncertain
# ---------------------------------------------------------------------------
def make_invoice_review():
    doc = _doc("sample_invoice_review.pdf")
    story = [
        _heading("COMMERCIAL INVOICE"),
        Paragraph("Invoice No: INV-20240277   Date: 2024-05-08", STYLES["Normal"]),
        Spacer(1, 0.5 * cm),
        _subheading("Seller"),
        _field_table([
            ("Company", "Beijing Precision Instruments Ltd."),
            ("Address", "Tower B, Zhongguancun Science Park, Beijing 100190, China"),
            ("Tax ID", "9111010078885XXX"),
            ("Bank", "Bank of China, Branch 0118, A/C 620200XXXXXXXX"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Buyer / Consignee"),
        _field_table([
            # Abbreviated name — the fuzzy match may mark this as uncertain
            ("Company", "ACME IMPORTS"),
            ("Address", "Plot 42, MIDC Industrial Area, Navi Mumbai 400705, India"),
            ("IEC Code", "AABCA1234C"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Shipment & Terms"),
        _field_table([
            ("Port of Loading", "CNBJS"),
            ("Port of Discharge", "INNSA"),
            ("Incoterms", "CIF"),
            ("Mode", "Sea Freight — FCL"),
            ("Payment Terms", "T/T 30 days after BL date"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Line Items"),
        Table(
            [
                ["#", "Description", "HS Code", "Qty", "Unit Price (USD)", "Amount (USD)"],
                ["1", "Digital Pressure Sensors", "9026.20", "500 pcs", "48.00", "24,000.00"],
                ["2", "Calibration Kits", "9026.20", "50 sets", "120.00", "6,000.00"],
                ["3", "Spare O-Ring Packs", "8484.10", "200 packs", "8.50", "1,700.00"],
            ],
            colWidths=[1 * cm, 5 * cm, 2.5 * cm, 2 * cm, 3 * cm, 3 * cm],
        ),
        Spacer(1, 0.3 * cm),
        _field_table([
            ("Sub-total", "USD 31,700.00"),
            ("Freight", "USD 1,200.00"),
            ("Insurance", "USD 65.00"),
            ("Total Invoice Value", "USD 32,965.00"),
            ("Gross Weight", "680.00 KG"),
            ("Invoice Number", "INV-20240277"),
        ]),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "We hereby certify that this invoice is true and correct and that the goods "
            "described are of Chinese origin.",
            STYLES["Normal"],
        ),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "Authorised Signatory: ________________________   Date: 2024-05-08",
            STYLES["Normal"],
        ),
    ]
    doc.build(story)
    print("Created:", OUT_DIR / "sample_invoice_review.pdf")


# ---------------------------------------------------------------------------
# 4. sample_textiles002_approve.pdf  — all fields match TEXTILES_002 → approve
# ---------------------------------------------------------------------------
def make_textiles_approve():
    doc = _doc("sample_textiles002_approve.pdf")
    story = [
        _heading("BILL OF LADING"),
        Paragraph("AsiaLine Freight — B/L No. AL-2024-00892", STYLES["Normal"]),
        Spacer(1, 0.5 * cm),
        _subheading("Shipper / Exporter"),
        _field_table([
            ("Company Name", "Ningbo Textile Manufacturing Co., Ltd."),
            ("Address", "22 Harbour Industrial Zone, Ningbo, 315000, China"),
            ("Contact", "+86 574 8765 4321"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Consignee"),
        _field_table([
            ("Company Name", "Sunrise Textiles Pvt Ltd"),
            ("Address", "Plot 18, APMC Industrial Estate, Mumbai, Maharashtra 400018, India"),
            ("GSTIN", "27ABRCS5678D1ZK"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Shipment Details"),
        _field_table([
            ("Port of Loading", "CNNGB"),
            ("Port of Discharge", "INBOM"),
            ("Incoterms", "FOB"),
            ("Vessel / Voyage", "MV Cosco Shipping Star  /  Voyage 033W"),
            ("Bill of Lading Date", "2024-06-10"),
            ("B/L Type", "Original — negotiable"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Cargo Description"),
        _field_table([
            ("Description of Goods", "Woven Cotton Fabrics — Bleached"),
            ("HS Code", "5208.12"),
            ("Gross Weight", "4200.00 KG"),
            ("Measurement", "22.50 CBM"),
            ("Packages", "840 bales"),
            ("Invoice Number", "ST-240610"),
            ("Invoice Date", "2024-06-05"),
            ("Invoice Value", "USD 63,000.00"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Freight & Charges"),
        _field_table([
            ("Freight Terms", "COLLECT"),
            ("Ocean Freight", "USD 2,100.00"),
            ("THC — Origin", "USD 310.00"),
        ]),
        Spacer(1, 0.6 * cm),
        Paragraph(
            "Signed for the carrier AsiaLine Freight by its authorised agent.",
            STYLES["Italic"],
        ),
    ]
    doc.build(story)
    print("Created:", OUT_DIR / "sample_textiles002_approve.pdf")


# ---------------------------------------------------------------------------
# 5. sample_textiles002_amend.pdf  — wrong incoterms (CIF instead of FOB)
#                                  + wrong port of discharge (INNSA not INBOM)
#                                  → amend (2 hard mismatches)
# ---------------------------------------------------------------------------
def make_textiles_amend():
    doc = _doc("sample_textiles002_amend.pdf")
    story = [
        _heading("BILL OF LADING"),
        Paragraph("StarShip Logistics — B/L No. SS-2024-01144", STYLES["Normal"]),
        Spacer(1, 0.5 * cm),
        _subheading("Shipper / Exporter"),
        _field_table([
            ("Company Name", "Suzhou Fabric Group Co., Ltd."),
            ("Address", "58 Textile Park, Suzhou, 215004, China"),
            ("Contact", "+86 512 6543 9900"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Consignee"),
        _field_table([
            ("Company Name", "Sunrise Textiles Pvt Ltd"),
            ("Address", "Plot 18, APMC Industrial Estate, Mumbai, Maharashtra 400018, India"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Shipment Details"),
        _field_table([
            ("Port of Loading", "CNSHA"),
            # Wrong: INNSA (Navi Mumbai) instead of INBOM (Mumbai) — hard mismatch
            ("Port of Discharge", "INNSA"),
            # Wrong: CIF instead of FOB — hard mismatch
            ("Incoterms", "CIF"),
            ("Vessel / Voyage", "MV One Harmony  /  Voyage 021E"),
            ("Bill of Lading Date", "2024-07-15"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Cargo Description"),
        _field_table([
            ("Description of Goods", "Unbleached Woven Cotton Fabrics"),
            ("HS Code", "5208.11"),
            ("Gross Weight", "3800.00 KG"),
            ("Measurement", "20.00 CBM"),
            ("Packages", "760 bales"),
            ("Invoice Number", "ST-240715"),
            ("Invoice Value", "USD 57,000.00"),
        ]),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "<b>Discrepancy Notice:</b> Incoterms show CIF (cost + insurance + freight "
            "included) but the contract specifies FOB. Port of discharge shows INNSA "
            "instead of the agreed INBOM. Please issue corrected documents.",
            STYLES["Normal"],
        ),
        Spacer(1, 0.6 * cm),
        Paragraph(
            "Signed for the carrier StarShip Logistics by its authorised agent.",
            STYLES["Italic"],
        ),
    ]
    doc.build(story)
    print("Created:", OUT_DIR / "sample_textiles002_amend.pdf")


# ---------------------------------------------------------------------------
# 6. sample_elecparts003_approve.pdf  — all fields match ELECPARTS_003 → approve
# ---------------------------------------------------------------------------
def make_elecparts_approve():
    doc = _doc("sample_elecparts003_approve.pdf")
    story = [
        _heading("COMMERCIAL INVOICE & PACKING LIST"),
        Paragraph("Invoice No: TP-20241087   Date: 2024-08-20", STYLES["Normal"]),
        Spacer(1, 0.5 * cm),
        _subheading("Seller"),
        _field_table([
            ("Company", "Shenzhen MicroChip Electronics Ltd."),
            ("Address", "Block 7, Hi-Tech Industrial Park, Shenzhen, 518057, China"),
            ("Tax ID", "9144030078XXXXXX"),
            ("Bank", "HSBC Shenzhen, A/C 621XXX"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Buyer / Consignee"),
        _field_table([
            ("Company", "TechParts Global India Pvt Ltd"),
            ("Address", "14 SIPCOT IT Park, Siruseri, Chennai, Tamil Nadu 603103, India"),
            ("IEC Code", "AABCT6789D"),
            ("GSTIN", "33AABCT6789D1ZM"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Shipment & Terms"),
        _field_table([
            ("Port of Loading", "CNSZX"),
            ("Port of Discharge", "INMAA"),
            ("Incoterms", "DAP"),
            ("Mode", "Sea Freight — LCL"),
            ("Payment Terms", "L/C at sight"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Line Items"),
        Table(
            [
                ["#", "Description", "HS Code", "Qty", "Unit Price (USD)", "Total (USD)"],
                ["1", "Silicon Diodes — General Purpose", "8541.10", "10,000 pcs", "0.85", "8,500.00"],
                ["2", "NPN Signal Transistors", "8541.21", "5,000 pcs", "1.20", "6,000.00"],
                ["3", "PNP Power Transistors", "8541.29", "2,000 pcs", "3.75", "7,500.00"],
            ],
            colWidths=[1 * cm, 5.5 * cm, 2.5 * cm, 2 * cm, 3 * cm, 3 * cm],
        ),
        Spacer(1, 0.3 * cm),
        _field_table([
            ("Sub-total", "USD 22,000.00"),
            ("Freight (DAP)", "USD 1,800.00"),
            ("Insurance", "USD 44.00"),
            ("Total Invoice Value", "USD 23,844.00"),
            ("Gross Weight", "185.50 KG"),
            ("Invoice Number", "TP-20241087"),
        ]),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "We certify that the goods described herein are of Chinese origin and comply "
            "with all applicable export regulations.",
            STYLES["Normal"],
        ),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "Authorised Signatory: ________________________   Date: 2024-08-20",
            STYLES["Normal"],
        ),
    ]
    doc.build(story)
    print("Created:", OUT_DIR / "sample_elecparts003_approve.pdf")


# ---------------------------------------------------------------------------
# 7. sample_elecparts003_amend.pdf  — wrong HS code + wrong port of discharge
#                                   → amend (2 hard mismatches)
# ---------------------------------------------------------------------------
def make_elecparts_amend():
    doc = _doc("sample_elecparts003_amend.pdf")
    story = [
        _heading("COMMERCIAL INVOICE"),
        Paragraph("Invoice No: TP-20241203   Date: 2024-09-05", STYLES["Normal"]),
        Spacer(1, 0.5 * cm),
        _subheading("Seller"),
        _field_table([
            ("Company", "Taiwan Semiconductor Components Co., Ltd."),
            ("Address", "12F, No. 100 Zhongshan Rd, Kaohsiung 80491, Taiwan"),
            ("Tax ID", "54321XXX"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Buyer / Consignee"),
        _field_table([
            ("Company", "TechParts Global India Pvt Ltd"),
            ("Address", "14 SIPCOT IT Park, Siruseri, Chennai, Tamil Nadu 603103, India"),
            ("IEC Code", "AABCT6789D"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Shipment & Terms"),
        _field_table([
            ("Port of Loading", "TWKHH"),
            # Wrong: INNSA instead of INMAA — hard mismatch
            ("Port of Discharge", "INNSA"),
            ("Incoterms", "DAP"),
            ("Mode", "Sea Freight — FCL"),
            ("Payment Terms", "T/T 60 days"),
        ]),
        Spacer(1, 0.4 * cm),
        _subheading("Line Items"),
        Table(
            [
                ["#", "Description", "HS Code", "Qty", "Unit Price (USD)", "Total (USD)"],
                # HS code 8473.30 is NOT in ELECPARTS_003 allowed list — hard mismatch
                ["1", "Printed Circuit Board Assemblies", "8473.30", "500 pcs", "45.00", "22,500.00"],
                ["2", "Integrated Circuit Modules", "8542.31", "1,200 pcs", "12.50", "15,000.00"],
            ],
            colWidths=[1 * cm, 5.5 * cm, 2.5 * cm, 2 * cm, 3 * cm, 3 * cm],
        ),
        Spacer(1, 0.3 * cm),
        _field_table([
            ("Sub-total", "USD 37,500.00"),
            ("Freight (DAP)", "USD 2,400.00"),
            ("Insurance", "USD 75.00"),
            ("Total Invoice Value", "USD 39,975.00"),
            ("Gross Weight", "410.00 KG"),
            ("Invoice Number", "TP-20241203"),
        ]),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "<b>Issue:</b> Line item 1 HS code 8473.30 (parts for office machines) is not "
            "part of the agreed semiconductor classification. Port of discharge INNSA "
            "does not match the contracted destination INMAA (Chennai). "
            "Please reissue with corrected values.",
            STYLES["Normal"],
        ),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "Authorised Signatory: ________________________   Date: 2024-09-05",
            STYLES["Normal"],
        ),
    ]
    doc.build(story)
    print("Created:", OUT_DIR / "sample_elecparts003_amend.pdf")


if __name__ == "__main__":
    make_bol_approve()
    make_bol_amend()
    make_invoice_review()
    make_textiles_approve()
    make_textiles_amend()
    make_elecparts_approve()
    make_elecparts_amend()
    print("\nAll samples written to:", OUT_DIR)
