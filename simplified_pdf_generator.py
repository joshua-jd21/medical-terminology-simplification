from io import BytesIO
import re
import unicodedata
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Flowable,
    KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String


# ============================================================
# COLOR PALETTE (Modern Clinical Teal & Slate)
# ============================================================

PRIMARY_NAVY = colors.HexColor("#0F3D5E")
PRIMARY_TEAL = colors.HexColor("#0D9488")
DARK_TEAL = colors.HexColor("#0F766E")
LIGHT_TEAL_BG = colors.HexColor("#F0FDFA")
SOFT_BLUE_BG = colors.HexColor("#F0F7FF")
SLATE_900 = colors.HexColor("#0F172A")
SLATE_700 = colors.HexColor("#334155")
SLATE_500 = colors.HexColor("#64748B")
SLATE_200 = colors.HexColor("#E2E8F0")
SLATE_100 = colors.HexColor("#F8FAFC")
AMBER_ACCENT = colors.HexColor("#D97706")
WHITE = colors.white


# ============================================================
# CUSTOM INTERACTIVE & GRAPHICAL FLOWABLES
# ============================================================

class BookmarkAnchor(Flowable):
    """Registers an invisible PDF outline bookmark and internal destination."""

    def __init__(self, key: str, title: str, level: int = 0):
        super().__init__()
        self.key = key
        self.title = title
        self.level = level
        self.width = 0
        self.height = 0

    def draw(self):
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, level=self.level, closed=False)


class InteractiveCheckbox(Flowable):
    """Renders a clickable PDF AcroForm checkbox with vector fallback."""

    def __init__(self, name: str, tooltip: str = "Click to check off", size: int = 13):
        super().__init__()
        self.name = name
        self.tooltip = tooltip
        self.size = size
        self.width = size + 4
        self.height = size + 4

    def draw(self):
        try:
            self.canv.acroForm.checkbox(
                name=self.name,
                tooltip=self.tooltip,
                checked=False,
                x=2,
                y=2,
                buttonStyle="check",
                borderStyle="solid",
                borderWidth=1.2,
                borderColor=PRIMARY_TEAL,
                fillColor=LIGHT_TEAL_BG,
                textColor=DARK_TEAL,
                forceBorder=True,
                size=self.size,
            )
        except Exception:
            self.canv.setStrokeColor(PRIMARY_TEAL)
            self.canv.setFillColor(LIGHT_TEAL_BG)
            self.canv.rect(2, 2, self.size, self.size, stroke=1, fill=1)


def build_summary_dashboard(total_terms: int, total_words: int, unique_terms: int) -> Drawing:
    """Builds a graphical vector dashboard showing document simplification metrics."""
    width = 468
    height = 74
    d = Drawing(width, height)

    # Outer container card
    d.add(Rect(0, 0, width, height, rx=8, ry=8, fillColor=SLATE_100, strokeColor=SLATE_200, strokeWidth=1))

    # Three KPI Metric Cards across the top
    card_w = (width - 36) / 3
    card_h = 54
    card_y = height - card_h - 10

    kpis = [
        (str(total_terms), "Terms Translated", PRIMARY_TEAL),
        (str(unique_terms), "Unique Concepts", PRIMARY_NAVY),
        (str(total_words), "Words Analyzed", AMBER_ACCENT),
    ]

    for idx, (val, label, accent) in enumerate(kpis):
        x = 10 + idx * (card_w + 8)
        d.add(Rect(x, card_y, card_w, card_h, rx=6, ry=6, fillColor=WHITE, strokeColor=SLATE_200, strokeWidth=0.8))
        d.add(Rect(x, card_y, 4, card_h, rx=2, ry=2, fillColor=accent, strokeColor=accent, strokeWidth=0))
        d.add(String(x + 14, card_y + 28, val, fontName="Helvetica-Bold", fontSize=18, fillColor=accent))
        d.add(String(x + 14, card_y + 11, label, fontName="Helvetica", fontSize=8.5, fillColor=SLATE_500))

    return d


# ============================================================
# TEXT NORMALIZATION & RICH FORMATTING HELPERS
# ============================================================

def clean_text(text: str) -> str:
    """Decomposes Unicode ligatures (ﬁ, ﬂ, ﬀ) into standard letters."""
    return unicodedata.normalize("NFKC", text or "").strip()


def format_simplified_paragraphs(simplified_text: str, identified_terms: list, styles: dict) -> list:
    """
    Converts raw simplified text into structured headings, metadata rows,
    and paragraphs with color-highlighted plain-English explanations.
    """
    flowables = []
    meanings = sorted(
        {clean_text(item.get("meaning", "")) for item in identified_terms if item.get("meaning")},
        key=len,
        reverse=True,
    )
    escaped_meanings = [re.escape(escape(m)) for m in meanings if m]
    meaning_pattern = (
        re.compile(r"\((" + "|".join(escaped_meanings) + r")\)", re.IGNORECASE)
        if escaped_meanings
        else None
    )

    lines = clean_text(simplified_text).splitlines()
    metadata_rows = []
    paragraph_buffer = []

    def flush_metadata():
        nonlocal metadata_rows
        if not metadata_rows:
            return
        meta_table = Table(metadata_rows, colWidths=[1.6 * inch, 4.9 * inch])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SOFT_BLUE_BG),
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#BFDBFE")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DBEAFE")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        flowables.append(meta_table)
        flowables.append(Spacer(1, 10))
        metadata_rows = []

    def flush_paragraph():
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        raw_para = " ".join(paragraph_buffer).strip()
        paragraph_buffer = []
        if not raw_para:
            return

        safe_html = escape(raw_para)
        if meaning_pattern:
            safe_html = meaning_pattern.sub(
                r'<font color="#0F766E"><b>(\1)</b></font>',
                safe_html,
            )
        flowables.append(Paragraph(safe_html, styles["body"]))
        flowables.append(Spacer(1, 7))

    meta_prefixes = ("patient name:", "age:", "gender:", "department:", "date:", "doctor:", "diagnosis:")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_metadata()
            flush_paragraph()
            continue

        lower_line = line.lower()

        if ":" in line and lower_line.startswith(meta_prefixes):
            flush_paragraph()
            key, val = line.split(":", 1)
            metadata_rows.append(
                [
                    Paragraph(f"<b>{escape(key.strip())}</b>", styles["meta_label"]),
                    Paragraph(escape(val.strip()), styles["meta_value"]),
                ]
            )
            continue

        flush_metadata()

        is_all_caps_title = line.isupper() and len(line) <= 65
        is_section_header = (
            len(line) <= 65
            and not line.endswith((".", ",", ";", ":"))
            and line[0].isupper()
            and len(line.split()) <= 8
        )

        if is_all_caps_title:
            flush_paragraph()
            flowables.append(Paragraph(escape(line.title()), styles["doc_subheading"]))
            flowables.append(Spacer(1, 6))
        elif is_section_header:
            flush_paragraph()
            flowables.append(Spacer(1, 4))
            flowables.append(Paragraph(escape(line), styles["doc_subheading"]))
            flowables.append(Spacer(1, 4))
        else:
            paragraph_buffer.append(line)

    flush_metadata()
    flush_paragraph()
    return flowables


# ============================================================
# PAGE HEADER & FOOTER CANVAS CALLBACKS
# ============================================================

def draw_page_chrome(canvas, doc):
    """Draws consistent running headers, footers, and page numbers."""
    canvas.saveState()
    page_num = canvas.getPageNumber()
    width, height = letter

    if page_num > 1:
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.setFillColor(PRIMARY_NAVY)
        canvas.drawString(0.9 * inch, height - 0.55 * inch, "MediSimplify AI  |  Patient-Friendly Medical Report")

        canvas.setStrokeColor(SLATE_200)
        canvas.setLineWidth(0.7)
        canvas.line(0.9 * inch, height - 0.63 * inch, width - 0.9 * inch, height - 0.63 * inch)

    canvas.setStrokeColor(SLATE_200)
    canvas.setLineWidth(0.7)
    canvas.line(0.9 * inch, 0.68 * inch, width - 0.9 * inch, 0.68 * inch)

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(SLATE_500)
    canvas.drawString(
        0.9 * inch,
        0.50 * inch,
        "Educational summary only - always confirm medical decisions with your healthcare provider.",
    )
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(PRIMARY_NAVY)
    canvas.drawRightString(width - 0.9 * inch, 0.50 * inch, f"Page {page_num}")

    canvas.restoreState()


# ============================================================
# MAIN PDF GENERATOR ENTRY POINT
# ============================================================

def generate_simplified_pdf(result: dict) -> bytes:
    """
    Generates an interactive, graphical, patient-friendly PDF report
    from the output dictionary of simplify_medical_text().
    """
    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        title="Simplified Medical Report - MediSimplify AI",
        author="MediSimplify AI",
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="main_frame",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="ReportTemplate", frames=[frame], onPage=draw_page_chrome)])

    original_text = clean_text(result.get("original_text", ""))
    simplified_text = clean_text(result.get("simplified_text", ""))
    identified_terms = result.get("identified_terms", []) or []
    tokens = result.get("tokens", []) or []
    total_terms = int(result.get("total_terms", len(identified_terms)))
    total_words = len(tokens) if tokens else len(original_text.split())

    seen_terms = set()
    unique_glossary = []
    for item in identified_terms:
        t = clean_text(item.get("term", ""))
        m = clean_text(item.get("meaning", ""))
        if t and t.lower() not in seen_terms:
            seen_terms.add(t.lower())
            unique_glossary.append((t, m))

    base_styles = getSampleStyleSheet()
    styles = {
        "banner_title": ParagraphStyle(
            "BannerTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "banner_date": ParagraphStyle(
            "BannerDate",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=WHITE,
            alignment=TA_RIGHT,
        ),
        "nav_bar": ParagraphStyle(
            "NavBar",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=12,
            textColor=PRIMARY_NAVY,
            alignment=TA_CENTER,
        ),
        "section_title": ParagraphStyle(
            "SectionTitle",
            parent=base_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=PRIMARY_NAVY,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "back_top": ParagraphStyle(
            "BackTop",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=PRIMARY_TEAL,
            alignment=TA_RIGHT,
        ),
        "doc_subheading": ParagraphStyle(
            "DocSubheading",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.8,
            leading=14,
            textColor=DARK_TEAL,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=SLATE_900,
        ),
        "meta_label": ParagraphStyle(
            "MetaLabel",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=PRIMARY_NAVY,
        ),
        "meta_value": ParagraphStyle(
            "MetaValue",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=SLATE_900,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=WHITE,
        ),
        "term_cell": ParagraphStyle(
            "TermCell",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.2,
            leading=13,
            textColor=PRIMARY_NAVY,
        ),
        "meaning_cell": ParagraphStyle(
            "MeaningCell",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            textColor=SLATE_700,
        ),
        "original_box": ParagraphStyle(
            "OriginalBox",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=13,
            textColor=SLATE_700,
        ),
    }

    story = []

    # 1. TOP ANCHOR & VISUAL HEADER BANNER
    story.append(BookmarkAnchor("top", "Report Overview", level=0))
    generated_on = datetime.now().strftime("%b %d, %Y")

    banner_data = [
        [
            Paragraph(
                '<a name="top"/>MediSimplify AI<br/><font size="9.5" color="#CCFBF1">Patient-Friendly Clinical Report &amp; Interactive Terminology Guide</font>',
                styles["banner_title"],
            ),
            Paragraph(f"Generated<br/>{generated_on}", styles["banner_date"]),
        ]
    ]
    banner_table = Table(banner_data, colWidths=[5.1 * inch, 1.4 * inch])
    banner_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_NAVY),
                ("LINEBELOW", (0, 0), (-1, -1), 3, PRIMARY_TEAL),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    story.append(banner_table)
    story.append(Spacer(1, 8))

    # 2. INTERACTIVE QUICK-JUMP NAVIGATION BAR
    nav_html = (
        '<a href="#simplified" color="#0F3D5E"><u>1. Simplified Report</u></a>'
        '&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;'
        '<a href="#glossary" color="#0F3D5E"><u>2. Medical Glossary (' + str(len(unique_glossary)) + ')</u></a>'
        '&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;'
        '<a href="#checklist" color="#0F3D5E"><u>3. Doctor Visit Checklist</u></a>'
        '&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;'
        '<a href="#original" color="#0F3D5E"><u>4. Original Clinical Text</u></a>'
    )
    nav_table = Table([[Paragraph(nav_html, styles["nav_bar"])]], colWidths=[6.5 * inch])
    nav_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_TEAL_BG),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#99F6E4")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(nav_table)
    story.append(Spacer(1, 10))

    # 3. GRAPHICAL METRICS DASHBOARD
    story.append(build_summary_dashboard(total_terms, total_words, len(unique_glossary)))
    story.append(Spacer(1, 14))

    # 4. SIMPLIFIED MEDICAL REPORT SECTION
    story.append(BookmarkAnchor("simplified", "1. Simplified Medical Report", level=0))
    sec1_header = Table(
        [
            [
                Paragraph('<a name="simplified"/>1. Simplified Medical Report', styles["section_title"]),
                Paragraph('<a href="#top" color="#0D9488"><u>Back to Top</u></a>', styles["back_top"]),
            ]
        ],
        colWidths=[5.3 * inch, 1.2 * inch],
    )
    sec1_header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, PRIMARY_TEAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(sec1_header)
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            '<font size="8.5" color="#64748B">Plain-English explanations are highlighted in '
            '<font color="#0F766E"><b>bold teal parentheses</b></font> right next to each medical term.</font>',
            styles["body"],
        )
    )
    story.append(Spacer(1, 8))

    story.extend(format_simplified_paragraphs(simplified_text, identified_terms, styles))
    story.append(Spacer(1, 12))

    # 5. VISUAL MEDICAL GLOSSARY TABLE
    if unique_glossary:
        story.append(BookmarkAnchor("glossary", "2. Quick-Reference Medical Glossary", level=0))
        sec2_header = Table(
            [
                [
                    Paragraph(
                        f'<a name="glossary"/>2. Quick-Reference Medical Glossary ({len(unique_glossary)} Terms)',
                        styles["section_title"],
                    ),
                    Paragraph('<a href="#top" color="#0D9488"><u>Back to Top</u></a>', styles["back_top"]),
                ]
            ],
            colWidths=[5.3 * inch, 1.2 * inch],
        )
        sec2_header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -1), 1.2, PRIMARY_TEAL),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(sec2_header)
        story.append(Spacer(1, 8))

        glossary_rows = [
            [
                Paragraph("Medical Term", styles["table_header"]),
                Paragraph("Plain-English Meaning", styles["table_header"]),
            ]
        ]
        for term, meaning in unique_glossary:
            glossary_rows.append(
                [
                    Paragraph(escape(term.capitalize()), styles["term_cell"]),
                    Paragraph(escape(meaning.capitalize()), styles["meaning_cell"]),
                ]
            )

        glossary_table = Table(glossary_rows, colWidths=[2.3 * inch, 4.2 * inch], repeatRows=1)
        glossary_style = [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.5, SLATE_200),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]
        for row_idx in range(1, len(glossary_rows)):
            bg_color = WHITE if row_idx % 2 == 1 else SLATE_100
            glossary_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg_color))

        glossary_table.setStyle(TableStyle(glossary_style))
        story.append(glossary_table)
        story.append(Spacer(1, 14))

    # 6. INTERACTIVE PATIENT CHECKLIST (CLICKABLE PDF CHECKBOXES)
    story.append(BookmarkAnchor("checklist", "3. Interactive Doctor Visit Checklist", level=0))
    sec3_header = Table(
        [
            [
                Paragraph('<a name="checklist"/>3. Interactive Doctor Visit Checklist', styles["section_title"]),
                Paragraph('<a href="#top" color="#0D9488"><u>Back to Top</u></a>', styles["back_top"]),
            ]
        ],
        colWidths=[5.3 * inch, 1.2 * inch],
    )
    sec3_header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, PRIMARY_TEAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    sample_terms = ", ".join(t for t, _ in unique_glossary[:4])
    checklist_items = [
        f"Ask my doctor to explain how my key findings ({sample_terms}) connect to my daily symptoms."
        if sample_terms
        else "Ask my doctor to walk through the key findings in this clinical report.",
        "Confirm which diagnostic tests or lab work are needed next and when results will be ready.",
        "Review all current medications, dosages, and potential side effects before leaving the clinic.",
        "Ask which warning signs require urgent medical attention versus routine follow-up.",
    ]

    checklist_rows = []
    for idx, item_text in enumerate(checklist_items, start=1):
        checklist_rows.append(
            [
                InteractiveCheckbox(name=f"patient_check_{idx}", tooltip=f"Check item {idx}"),
                Paragraph(escape(item_text), styles["meaning_cell"]),
            ]
        )

    checklist_table = Table(checklist_rows, colWidths=[0.35 * inch, 6.15 * inch])
    checklist_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_TEAL_BG),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#99F6E4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (0, -1), 8),
                ("LEFTPADDING", (1, 0), (1, -1), 4),
                ("RIGHTPADDING", (1, 0), (1, -1), 8),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                sec3_header,
                Spacer(1, 6),
                Paragraph(
                    '<font size="8.5" color="#64748B">Click the boxes directly inside your PDF viewer to track questions for your appointment:</font>',
                    styles["body"],
                ),
                Spacer(1, 6),
                checklist_table,
            ]
        )
    )
    story.append(Spacer(1, 14))

    # 7. ORIGINAL CLINICAL TEXT REFERENCE BOX (MULTI-ROW FOR PAGE SPLITTING)
    if original_text:
        story.append(BookmarkAnchor("original", "4. Original Clinical Text (Reference)", level=0))
        sec4_header = Table(
            [
                [
                    Paragraph(
                        '<a name="original"/>4. Original Clinical Text (For Clinician Reference)',
                        styles["section_title"],
                    ),
                    Paragraph('<a href="#top" color="#0D9488"><u>Back to Top</u></a>', styles["back_top"]),
                ]
            ],
            colWidths=[5.3 * inch, 1.2 * inch],
        )
        sec4_header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -1), 1.2, SLATE_500),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(sec4_header)
        story.append(Spacer(1, 6))

        orig_rows = [
            [Paragraph(escape(line.strip()), styles["original_box"])]
            for line in original_text.splitlines()
            if line.strip()
        ]
        if orig_rows:
            orig_box = Table(orig_rows, colWidths=[6.5 * inch])
            orig_box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SLATE_100),
                        ("BOX", (0, 0), (-1, -1), 0.75, SLATE_200),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )
            story.append(orig_box)

    doc.build(story)
    return buffer.getvalue()