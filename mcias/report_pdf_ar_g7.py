"""Arabic RTL executive PDF renderer using a locally installed font.

No font files, raw beneficiary details or external requests are included.
"""
from html import escape
from io import BytesIO
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from mcias.reporting_g7 import verify_snapshot, ReportBlocked

CANDIDATE_FONTS = (
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/opentype/fonts-hosny-amiri/Amiri-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
)
FONT_NAME = "MCIAS_G7_LocalArabic"

def font_path():
    configured = os.environ.get("MCIAS_ARABIC_FONT_PATH")
    if configured:
        if not Path(configured).is_file():
            raise ReportBlocked("configured local Arabic font is unavailable")
        return configured
    for item in CANDIDATE_FONTS:
        if Path(item).is_file():
            return item
    raise ReportBlocked("local Arabic TTF font required; set MCIAS_ARABIC_FONT_PATH")

def _ensure_font():
    location = font_path()
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, location))
        except Exception as exc:
            raise ReportBlocked("invalid local Arabic font") from exc
    return FONT_NAME

def rtl(value):
    return escape(get_display(reshape(str(value))))

def render_arabic_pdf(report):
    verify_snapshot(report)
    name = _ensure_font()
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, title="MCIAS - التقرير المالي",
        leftMargin=38, rightMargin=38, topMargin=48, bottomMargin=42,
        author="MCIAS - Local Audit System")
    title = ParagraphStyle("ar_title", fontName=name, fontSize=16,
                           leading=27, alignment=TA_RIGHT, textColor=colors.HexColor("#17324F"))
    body = ParagraphStyle("ar_body", fontName=name, fontSize=10,
                          leading=20, alignment=TA_RIGHT, textColor=colors.HexColor("#243B53"))
    cell = ParagraphStyle("ar_cell", fontName=name, fontSize=9,
                          leading=18, alignment=TA_RIGHT)
    story = [
        Paragraph(rtl("تقرير مراجعة المطالبات المالية"), title),
        Paragraph(rtl("نسخة ثابتة للأرشفة والمراجعة وليست أمراً بالصرف"), body),
        Spacer(1, 14),
        Paragraph(rtl("رقم النسخة: ") + escape(str(report.version)), body),
        Paragraph(rtl("عدد المطالبات: ") + escape(str(report.summary["total_claims"])), body),
        Paragraph(rtl("بصمة التقرير SHA-256: ") + escape(report.fingerprint), body),
        Spacer(1, 14),
    ]
    labels = ["الخصومات", "صافي المستحق", "المعلق", "المعتمد", "المطالب به", "العملة"]
    rows = [[Paragraph(rtl(x), cell) for x in labels]]
    for currency, values in sorted(report.summary["by_currency"].items()):
        row = [values["deductions"], values["payable"], values["held_claimed"],
               values["approved_claimed"], values["claimed"], currency]
        rows.append([Paragraph(rtl(x), cell) for x in row])
    tbl = Table(rows, repeatRows=1, hAlign="RIGHT",
                colWidths=[85, 91, 91, 91, 91, 70])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EDF5")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#153049")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6E0E9")),
    ]))
    story.extend([tbl, Spacer(1, 18),
        Paragraph(rtl("ملاحظة: المطالبات المعلقة والمرفوضة وغير المعتمدة لا تدخل في صافي المستحقات."), body),
        Paragraph(rtl("البيانات الشخصية وأرقام المستفيدين غير مدرجة في التقرير التنفيذي."), body)])
    audit = report.summary.get("audit")
    if audit:
        story.extend([Spacer(1, 12), Paragraph(rtl("نتائج التدقيق الاستشارية — الإصدار 2، دون قرار مالي"), body)])
        for state, count in audit["outcome_counts"].items():
            story.append(Paragraph(escape(f"{state}: {count}"), body))
        story.append(Paragraph(rtl(f"المكتمل تدقيقها: {audit['completed_audit_count']}، غير المكتمل: {audit['incomplete_audit_count']}، دون نتيجة مسجلة: {audit['unclassified_count']}"), body))
    doc.build(story)
    return output.getvalue()
