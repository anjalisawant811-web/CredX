"""
sar_report.py — Suspicious Activity Report (SAR) Generator for CredX
=====================================================================
Place this file at:  CredX/sar_report.py

Usage (standalone):
    python sar_report.py                        # generates report for ALL customers
    python sar_report.py --customer-id 3        # report for a single customer
    python sar_report.py --output reports/      # custom output directory

Flask route (add to app.py):
    from sar_report import generate_sar_report, get_sar_records
    @app.route("/sar")
    def sar():  ...

    @app.route("/api/sar/pdf")          ← ADD THIS ROUTE (see bottom of file)
    def sar_pdf_download():  ...

Dependencies:  flask, tabulate, reportlab
Install:  pip install reportlab
"""

import argparse
import math
import os
import sqlite3
from datetime import datetime

# ── Try tabulate for pretty CLI output; fall back to plain print ───────────────
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

# ── ReportLab for PDF generation ───────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.platypus import KeepTogether
from reportlab.lib.utils import ImageReader


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credx.db")

HIGH_RISK_THRESHOLD   = 70
MEDIUM_RISK_THRESHOLD = 40

MISSED_EMI_FLAG_THRESHOLD  = 2
LOW_BALANCE_EXPENSE_RATIO  = 0.80
HIGH_UTILIZATION_THRESHOLD = 75
LARGE_LOAN_MULTIPLIER      = 5

ACTIONS_MAP = {
    "High Risk": [
        "sms-alert",
        "credit-limit-reduced",
        "account-flagged",
        "relationship-manager-notified",
        "emi-restructuring-offer-sent",
    ],
    "Medium Risk": [
        "sms-alert",
        "proactive-wellness-email",
        "auto-debit-enrollment-suggested",
    ],
    "Low Risk": [
        "routine-monthly-monitoring",
        "loyalty-reward-eligible",
    ],
}

RISK_LEVEL_MAP = {
    "High Risk":   "HIGH",
    "Medium Risk": "MEDIUM",
    "Low Risk":    "LOW",
}

# ── Colour palette ─────────────────────────────────────────────────────────────
COL_BRAND    = colors.HexColor("#1a1f36")   # dark navy – header/brand
COL_BRAND2   = colors.HexColor("#2c3560")   # slightly lighter navy accent
COL_ACCENT   = colors.HexColor("#364fc7")   # bright indigo accent
COL_HIGH     = colors.HexColor("#dc3545")   # Bootstrap danger red
COL_MEDIUM   = colors.HexColor("#fd7e14")   # Bootstrap orange
COL_LOW      = colors.HexColor("#198754")   # Bootstrap success green
COL_LIGHT    = colors.HexColor("#f8f9fa")   # very light grey row fill
COL_LIGHT2   = colors.HexColor("#eef0f5")   # alternating row fill
COL_BORDER   = colors.HexColor("#dee2e6")   # Bootstrap border grey
COL_WHITE    = colors.white
COL_TEXT     = colors.HexColor("#212529")   # near-black body text
COL_MUTED    = colors.HexColor("#6c757d")   # muted grey text
COL_HIGH_BG  = colors.HexColor("#fff5f5")   # high risk card bg
COL_MED_BG   = colors.HexColor("#fff8f0")   # medium risk card bg
COL_LOW_BG   = colors.HexColor("#f0fff4")   # low risk card bg


# ─────────────────────────────────────────────────────────────────────────────
#  CORE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _compute_risk_score(income, expenses, missed_payments, credit_utilization):
    score = 0.0
    if income > 0:
        expense_ratio = expenses / income
        score += min(expense_ratio * 40, 40)
    score += min(missed_payments * 15, 30)
    score += min(credit_utilization * 0.3, 30)
    return round(min(score, 100))


def _classify_risk(score):
    if score >= HIGH_RISK_THRESHOLD:
        return "High Risk"
    if score >= MEDIUM_RISK_THRESHOLD:
        return "Medium Risk"
    return "Low Risk"


def _top_factors(income, expenses, missed_payments, credit_utilization, loan_amount):
    factors = []
    if income > 0 and expenses / income >= LOW_BALANCE_EXPENSE_RATIO:
        factors.append("High expense-to-income ratio")
    if missed_payments >= MISSED_EMI_FLAG_THRESHOLD:
        factors.append(f"Missed {missed_payments} EMI payment(s)")
    if credit_utilization >= HIGH_UTILIZATION_THRESHOLD:
        factors.append(f"Credit utilization at {credit_utilization:.0f}%")
    if income > 0 and loan_amount >= income * LARGE_LOAN_MULTIPLIER:
        factors.append("Loan exceeds 5× annual income")
    if not factors:
        factors.append("Normal financial profile")
    return factors


def _decision_logic(risk_class, factors):
    return (
        f"Classified as {risk_class} based on: "
        + "; ".join(factors) + "."
    )


def get_sar_records(customer_id: int = None, db_path: str = DB_PATH) -> list:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = "SELECT * FROM customers"
    params = ()
    if customer_id is not None:
        query += " WHERE id = ?"
        params = (customer_id,)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    records = []
    for row in rows:
        income            = float(row["income"]             or 0)
        expenses          = float(row["expenses"]            or 0)
        missed_payments   = int(  row["missed_payments"]    or 0)
        credit_util       = float(row["credit_utilization"] or 0)
        loan_amount       = float(row["loan_amount"]        or 0)

        score      = _compute_risk_score(income, expenses, missed_payments, credit_util)
        risk_class = _classify_risk(score)
        factors    = _top_factors(income, expenses, missed_payments, credit_util, loan_amount)
        logic      = _decision_logic(risk_class, factors)
        actions    = ACTIONS_MAP.get(risk_class, [])

        records.append({
            "customer_id":   row["id"],
            "customer_name": row["name"],
            "risk_score":    score,
            "risk_level":    RISK_LEVEL_MAP[risk_class],
            "top_factors":   factors,
            "decision_logic": logic,
            "action_taken":  actions,
            "timestamp":     datetime.now().strftime("%Y-%m-%d"),
        })

    records.sort(key=lambda r: r["risk_score"], reverse=True)
    return records


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def generate_sar_report(
    customer_id: int = None,
    output_dir: str = None,
    db_path: str = DB_PATH,
    fmt: str = "pdf",
) -> str:
    """
    Generate a SAR report file (PDF or TXT) and return its file path.
    """
    records = get_sar_records(customer_id=customer_id, db_path=db_path)
    if not records:
        print("[SAR] No customers found in the database.")
        return ""

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(db_path), "reports")
    os.makedirs(output_dir, exist_ok=True)

    ts_file  = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix   = f"_cid{customer_id}" if customer_id else "_all"
    filename = f"SAR_report{suffix}_{ts_file}.{fmt}"
    filepath = os.path.join(output_dir, filename)

    if fmt == "pdf":
        _write_pdf_report(records, filepath)
    else:
        _write_txt_report(records, filepath)

    print(f"[SAR] Report written -> {filepath}  ({len(records)} record(s))")
    return filepath


def generate_sar_pdf_bytes(customer_id: int = None, db_path: str = DB_PATH) -> bytes:
    """
    Generate a SAR PDF in-memory and return raw bytes (for Flask send_file).
    """
    import io
    records = get_sar_records(customer_id=customer_id, db_path=db_path)
    buf = io.BytesIO()
    _write_pdf_report(records, buf)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
#  PDF REPORT  (ReportLab — Enhanced Design)
# ─────────────────────────────────────────────────────────────────────────────

def _risk_colour(level: str) -> colors.Color:
    return {"HIGH": COL_HIGH, "MEDIUM": COL_MEDIUM}.get(level, COL_LOW)

def _risk_bg(level: str) -> colors.Color:
    return {"HIGH": COL_HIGH_BG, "MEDIUM": COL_MED_BG}.get(level, COL_LOW_BG)


def _build_pdf_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "SARTitle", parent=base["Normal"],
        fontSize=24, textColor=COL_WHITE,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
        spaceAfter=4,
    )
    styles["subtitle"] = ParagraphStyle(
        "SARSubtitle", parent=base["Normal"],
        fontSize=9, textColor=colors.HexColor("#adb5bd"),
        fontName="Helvetica", alignment=TA_LEFT, spaceAfter=0,
    )
    styles["section"] = ParagraphStyle(
        "SARSection", parent=base["Normal"],
        fontSize=12, textColor=COL_BRAND,
        fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=5,
    )
    styles["body"] = ParagraphStyle(
        "SARBody", parent=base["Normal"],
        fontSize=8.5, textColor=COL_TEXT,
        fontName="Helvetica", leading=13,
    )
    styles["small"] = ParagraphStyle(
        "SARSmall", parent=base["Normal"],
        fontSize=7.5, textColor=COL_MUTED,
        fontName="Helvetica", leading=11,
    )
    styles["small_white"] = ParagraphStyle(
        "SARSmallW", parent=base["Normal"],
        fontSize=7.5, textColor=COL_WHITE,
        fontName="Helvetica", leading=11,
    )
    styles["center_white"] = ParagraphStyle(
        "SARCenterW", parent=base["Normal"],
        fontSize=8, textColor=COL_WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER, leading=11,
    )
    styles["kpi_num"] = ParagraphStyle(
        "KPINum", parent=base["Normal"],
        fontSize=26, textColor=COL_WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER, leading=30,
    )
    styles["kpi_label"] = ParagraphStyle(
        "KPILabel", parent=base["Normal"],
        fontSize=7, textColor=COL_WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER,
        spaceAfter=2, letterSpacing=0.5,
    )
    styles["footer"] = ParagraphStyle(
        "SARFooter", parent=base["Normal"],
        fontSize=7, textColor=COL_MUTED,
        fontName="Helvetica", alignment=TA_CENTER, leading=10,
    )
    styles["card_name"] = ParagraphStyle(
        "CardName", parent=base["Normal"],
        fontSize=10, textColor=COL_WHITE,
        fontName="Helvetica-Bold", leading=13,
    )
    styles["card_score"] = ParagraphStyle(
        "CardScore", parent=base["Normal"],
        fontSize=10, textColor=COL_WHITE,
        fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=13,
    )
    styles["label"] = ParagraphStyle(
        "Label", parent=base["Normal"],
        fontSize=8, textColor=COL_BRAND,
        fontName="Helvetica-Bold", leading=12,
    )
    return styles


def _write_pdf_report(records: list, filepath) -> None:
    """filepath can be a file path string or a BytesIO buffer."""
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="CredX — Suspicious Activity Report",
        author="CredX AI Engine",
    )

    styles = _build_pdf_styles()
    story  = []
    W      = A4[0] - 28 * mm   # usable width
    gen_ts = datetime.now().strftime("%d %b %Y  %H:%M:%S")

    # ── COVER HEADER ──────────────────────────────────────────────────────────
    shield = Paragraph("🛡", ParagraphStyle(
        "Shield", fontSize=28, alignment=TA_CENTER,
        textColor=COL_WHITE, fontName="Helvetica-Bold",
    ))

    title_block = Table([
        [shield, Paragraph("Suspicious Activity Report", styles["title"])],
        ["",     Paragraph(
            f"CredX AI Compliance Engine  ·  Generated: {gen_ts}  ·  {len(records)} record(s)",
            styles["subtitle"]
        )],
    ], colWidths=[14 * mm, W - 14 * mm])
    title_block.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))

    cover_outer = Table([[title_block]], colWidths=[W])
    cover_outer.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), COL_BRAND),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING",   (0, 0), (-1, -1), 18),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 18),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), 8),
    ]))
    story.append(cover_outer)
    story.append(Spacer(1, 6 * mm))

    # ── KPI STRIP ─────────────────────────────────────────────────────────────
    high_n   = sum(1 for r in records if r["risk_level"] == "HIGH")
    medium_n = sum(1 for r in records if r["risk_level"] == "MEDIUM")
    low_n    = sum(1 for r in records if r["risk_level"] == "LOW")

    def kpi_cell(label, value, bg, accent_bar_colour):
        """Build a stylish KPI card with a top colour bar."""
        # Top accent bar
        bar = Table([[""]], colWidths=[(W - 9 * mm) / 4], rowHeights=[4])
        bar.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), accent_bar_colour),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        inner = Table([
            [bar],
            [Paragraph(str(value), styles["kpi_num"])],
            [Paragraph(label.upper(), styles["kpi_label"])],
        ], colWidths=[(W - 9 * mm) / 4])
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 2), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))
        return inner

    kpi_row = [[
        kpi_cell("High Risk",    high_n,      COL_WHITE, COL_HIGH),
        kpi_cell("Medium Risk",  medium_n,    COL_WHITE, COL_MEDIUM),
        kpi_cell("Low Risk",     low_n,       COL_WHITE, COL_LOW),
        kpi_cell("Total",        len(records),COL_WHITE, COL_ACCENT),
    ]]
    col_w = (W - 9 * mm) / 4
    kpi_tbl = Table(kpi_row, colWidths=[col_w] * 4, hAlign="LEFT")
    kpi_tbl.setStyle(TableStyle([
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (3, 0), (3, 0),   0),
        ("LINEAFTER",    (0, 0), (2, 0),   0.5, COL_BORDER),
        ("BOX",          (0, 0), (-1, -1), 0.5, COL_BORDER),
        ("ROUNDEDCORNERS",(0, 0),(-1, -1), 6),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 7 * mm))

    # ── RECORDS TABLE ─────────────────────────────────────────────────────────
    story.append(Paragraph("Customer Risk Records", styles["section"]))
    story.append(HRFlowable(width=W, thickness=1.5, color=COL_ACCENT, spaceAfter=5))

    col_widths = [
        11 * mm,   # ID
        30 * mm,   # Name
        14 * mm,   # Score
        18 * mm,   # Level
        52 * mm,   # Top Factors
        52 * mm,   # Actions
        16 * mm,   # Date
    ]

    tbl_header = [
        Paragraph("<b>ID</b>",            styles["small_white"]),
        Paragraph("<b>Customer</b>",      styles["small_white"]),
        Paragraph("<b>Score</b>",         styles["small_white"]),
        Paragraph("<b>Risk Level</b>",    styles["small_white"]),
        Paragraph("<b>Top Factors</b>",   styles["small_white"]),
        Paragraph("<b>Actions Taken</b>", styles["small_white"]),
        Paragraph("<b>Date</b>",          styles["small_white"]),
    ]
    tbl_data = [tbl_header]

    for rec in records:
        lvl = rec["risk_level"]
        clr = _risk_colour(lvl)
        score = rec["risk_score"]

        # Score circle badge
        score_para = Paragraph(
            f'<b>{score}</b>',
            ParagraphStyle("Sc", parent=styles["body"], alignment=TA_CENTER,
                           fontSize=9, textColor=COL_WHITE, fontName="Helvetica-Bold")
        )
        score_cell = Table([[score_para]], colWidths=[11 * mm], rowHeights=[11 * mm])
        score_cell.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), clr),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("ROUNDEDCORNERS",(0, 0), (-1, -1), 5),
        ]))

        # Level badge
        level_para = Paragraph(
            f'<b>{lvl}</b>',
            ParagraphStyle("Lv", parent=styles["body"], alignment=TA_CENTER,
                           fontSize=7.5, textColor=COL_WHITE, fontName="Helvetica-Bold")
        )
        level_cell = Table([[level_para]], colWidths=[15 * mm])
        level_cell.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), clr),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROUNDEDCORNERS",(0, 0), (-1, -1), 4),
        ]))

        factors_text = "\n".join(f"• {f}" for f in rec["top_factors"])
        actions_text = "\n".join(f"→ {a}" for a in rec["action_taken"])

        row = [
            Paragraph(f'<b>{rec["customer_id"]}</b>', styles["body"]),
            Paragraph(f'<b>{rec["customer_name"]}</b>', styles["body"]),
            score_cell,
            level_cell,
            Paragraph(factors_text,     styles["small"]),
            Paragraph(actions_text,     styles["small"]),
            Paragraph(rec["timestamp"], styles["small"]),
        ]
        tbl_data.append(row)

    rec_tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
    rec_style = TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0), COL_BRAND),
        ("TEXTCOLOR",     (0, 0), (-1, 0), COL_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("LINEBELOW",     (0, 0), (-1, 0), 2, COL_ACCENT),
        # Body rows
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        # Grid
        ("LINEBELOW",     (0, 1), (-1, -1), 0.3, COL_BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.5, COL_BORDER),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), 6),
    ])
    # Alternating rows
    for i in range(1, len(tbl_data)):
        bg = COL_LIGHT2 if i % 2 == 0 else COL_WHITE
        rec_style.add("BACKGROUND", (0, i), (-1, i), bg)

    rec_tbl.setStyle(rec_style)
    story.append(rec_tbl)
    story.append(Spacer(1, 8 * mm))

    # ── DETAILED DECISION CARDS ────────────────────────────────────────────────
    story.append(Paragraph("Detailed Decision Cards", styles["section"]))
    story.append(HRFlowable(width=W, thickness=1.5, color=COL_ACCENT, spaceAfter=6))

    for rec in records:
        lvl = rec["risk_level"]
        clr = _risk_colour(lvl)
        bg  = _risk_bg(lvl)

        # Card header
        hdr_left  = Paragraph(
            f'<b>{rec["customer_name"]}</b>',
            styles["card_name"]
        )
        hdr_id    = Paragraph(
            f'Customer #{rec["customer_id"]}  ·  {rec["timestamp"]}',
            ParagraphStyle("HdrId", parent=styles["small"], textColor=colors.HexColor("#cdd5e0"))
        )
        hdr_score = Paragraph(
            f'<b>{lvl}  {rec["risk_score"]}/100</b>',
            styles["card_score"]
        )

        hdr_left_col = Table([[hdr_left], [hdr_id]], colWidths=[W * 0.6])
        hdr_left_col.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))

        hdr_tbl = Table([[hdr_left_col, hdr_score]], colWidths=[W * 0.65, W * 0.35])
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), clr),
            ("TOPPADDING",    (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))

        # Card body — two-column layout
        factor_items = "\n".join(f"  • {f}" for f in rec["top_factors"])
        action_items = "\n".join(f"  → {a}" for a in rec["action_taken"])

        body_left = Table([
            [Paragraph("<b>Top Risk Factors</b>", styles["label"])],
            [Paragraph(factor_items, styles["small"])],
            [Spacer(1, 3)],
            [Paragraph("<b>Decision Logic</b>", styles["label"])],
            [Paragraph(rec["decision_logic"], styles["small"])],
        ], colWidths=[W / 2 - 6 * mm])
        body_left.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))

        body_right = Table([
            [Paragraph("<b>Actions Taken</b>", styles["label"])],
            [Paragraph(action_items, styles["small"])],
        ], colWidths=[W / 2 - 6 * mm])
        body_right.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))

        body_outer = Table([[body_left, body_right]], colWidths=[W / 2, W / 2])
        body_outer.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LINEAFTER",     (0, 0), (0, -1),  0.5, COL_BORDER),
        ]))

        card = KeepTogether([hdr_tbl, body_outer, Spacer(1, 5 * mm)])
        story.append(card)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=COL_BORDER))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"CredX AI Risk Engine  |  CONFIDENTIAL — For Internal Use Only  |  {gen_ts}",
        styles["footer"]
    ))

    doc.build(story)


# ─────────────────────────────────────────────────────────────────────────────
#  TEXT REPORT FORMATTER (kept as fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _write_txt_report(records: list, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        header = (
            "=" * 80 + "\n"
            "         CREDX — SUSPICIOUS ACTIVITY REPORT (SAR)\n"
            f"         Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"         Total Records: {len(records)}\n"
            + "=" * 80 + "\n\n"
        )
        f.write(header)
        for rec in records:
            f.write("-" * 80 + "\n")
            f.write(f"Customer ID   : {rec['customer_id']}\n")
            f.write(f"Customer Name : {rec['customer_name']}\n")
            f.write(f"Risk Score    : {rec['risk_score']} / 100\n")
            f.write(f"Risk Level    : {rec['risk_level']}\n")
            f.write(f"Timestamp     : {rec['timestamp']}\n")
            f.write("Top Factors   :\n")
            for factor in rec["top_factors"]:
                f.write(f"              • {factor}\n")
            f.write(f"Decision Logic:\n  {rec['decision_logic']}\n")
            f.write("Action Taken  :\n")
            for action in rec["action_taken"]:
                f.write(f"              -> {action}\n")
            f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
#  CLI SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def _print_cli_summary(records: list) -> None:
    rows = []
    for r in records:
        rows.append([
            r["customer_id"],
            r["customer_name"],
            r["risk_score"],
            r["risk_level"],
            "; ".join(r["top_factors"])[:55],
            ", ".join(r["action_taken"])[:40],
            r["timestamp"],
        ])
    headers = ["Cust ID", "Name", "Score", "Level", "Top Factors", "Actions Taken", "Date"]
    print("\n" + "=" * 90)
    print("  CREDX — SUSPICIOUS ACTIVITY REPORT (SAR)")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Records: {len(records)}")
    print("=" * 90)
    if HAS_TABULATE:
        print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    else:
        print("  " + " | ".join(f"{h:<15}" for h in headers))
        print("  " + "-" * 85)
        for row in rows:
            print("  " + " | ".join(f"{str(v):<15}" for v in row))
    print("=" * 90 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
#  FLASK INTEGRATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def flask_sar_json_response(customer_id: int = None):
    """Returns a dict suitable for jsonify() in a Flask /api/sar route."""
    records = get_sar_records(customer_id=customer_id)
    return {
        "report_type":   "Suspicious Activity Report (SAR)",
        "generated_at":  datetime.now().isoformat(),
        "total_records": len(records),
        "records":       records,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  FLASK ROUTE SNIPPET  — paste into app.py
# ─────────────────────────────────────────────────────────────────────────────
#
#   from flask import send_file
#   from sar_report import generate_sar_pdf_bytes
#
#   @app.route("/api/sar/pdf")
#   def sar_pdf_download():
#       cid = request.args.get("customer_id", type=int)
#       buf = generate_sar_pdf_bytes(customer_id=cid)
#       ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
#       return send_file(
#           buf,
#           mimetype="application/pdf",
#           as_attachment=True,
#           download_name=f"SAR_Report_{ts}.pdf",
#       )
#
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CredX — SAR Report Generator",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--customer-id", "-c", type=int, default=None, metavar="ID",
                        help="Generate report for a single customer ID (default: all)")
    parser.add_argument("--output", "-o", type=str, default=None, metavar="DIR",
                        help="Output directory for report files (default: CredX/reports/)")
    parser.add_argument("--format", "-f", type=str, choices=["pdf", "txt", "both"],
                        default="pdf", help="Output format: pdf | txt | both (default: pdf)")
    parser.add_argument("--db", type=str, default=DB_PATH, metavar="PATH",
                        help=f"Path to SQLite DB (default: {DB_PATH})")
    parser.add_argument("--no-file", action="store_true",
                        help="Print summary to terminal only; do not write files")
    args = parser.parse_args()

    records = get_sar_records(customer_id=args.customer_id, db_path=args.db)
    if not records:
        print("[SAR] No records found. Make sure the DB has customers.")
        return

    _print_cli_summary(records)

    if not args.no_file:
        fmts = ["pdf", "txt"] if args.format == "both" else [args.format]
        for fmt in fmts:
            generate_sar_report(
                customer_id=args.customer_id,
                output_dir=args.output,
                db_path=args.db,
                fmt=fmt,
            )


if __name__ == "__main__":
    main()