from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas import EducationItem, ExperienceItem, OptimizedCV, ProjectItem


FONT_NAME = "Helvetica"
ARABIC_FONT_NAME = "SmartCVArabic"


def render_cv_pdf(cv: OptimizedCV) -> bytes:
    is_rtl = cv.language.lower() == "arabic" or _has_arabic(cv.summary)
    font_name = _register_unicode_font() if is_rtl else FONT_NAME
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=_plain(cv.full_name or cv.target_title or "Optimized CV"),
    )
    styles = _styles(font_name, is_rtl)
    story: list = []

    name = cv.full_name.strip() or ("Candidate" if not is_rtl else "المرشح")
    title = cv.target_title.strip()
    story.append(Paragraph(_shape(name, is_rtl), styles["Name"]))
    if title:
        story.append(Paragraph(_shape(title, is_rtl), styles["Title"]))

    contact_parts = [part for part in [cv.contact_line, cv.location, " | ".join(cv.links)] if part]
    if contact_parts:
        story.append(Paragraph(_shape(" | ".join(contact_parts), is_rtl), styles["Contact"]))
    story.append(Spacer(1, 7))

    _section(story, styles, "Professional Summary", "الملخص المهني", cv.summary, is_rtl)
    _list_section(story, styles, "Core Skills", "المهارات الأساسية", cv.core_skills, is_rtl, inline=True)
    _list_section(story, styles, "Technical Skills", "المهارات التقنية", cv.technical_skills, is_rtl, inline=True)
    _experience_section(story, styles, "Professional Experience", "الخبرة العملية", cv.experience, is_rtl)
    _projects_section(story, styles, "Selected Projects", "المشاريع المختارة", cv.projects, is_rtl)
    _education_section(story, styles, "Education", "التعليم", cv.education, is_rtl)
    _list_section(story, styles, "Certifications", "الشهادات", cv.certifications, is_rtl)
    _experience_section(story, styles, "Additional", "معلومات إضافية", cv.additional_sections, is_rtl)

    document.build(story)
    return buffer.getvalue()


def _styles(font_name: str, is_rtl: bool) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    alignment = TA_RIGHT if is_rtl else TA_LEFT
    return {
        "Name": ParagraphStyle(
            "Name",
            parent=base["Title"],
            fontName=font_name,
            fontSize=20,
            leading=24,
            alignment=alignment,
            textColor=colors.HexColor("#111827"),
            spaceAfter=2,
        ),
        "Title": ParagraphStyle(
            "Title",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=10.5,
            leading=14,
            alignment=alignment,
            textColor=colors.HexColor("#2563eb"),
            spaceAfter=2,
        ),
        "Contact": ParagraphStyle(
            "Contact",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=8.5,
            leading=12,
            alignment=alignment,
            textColor=colors.HexColor("#4b5563"),
        ),
        "Section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=10.5,
            leading=13,
            alignment=alignment,
            textColor=colors.HexColor("#111827"),
            borderColor=colors.HexColor("#d1d5db"),
            borderWidth=0,
            borderPadding=0,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=9,
            leading=12.5,
            alignment=alignment,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=3,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=8.8,
            leading=12,
            alignment=alignment,
            leftIndent=0 if is_rtl else 10,
            rightIndent=10 if is_rtl else 0,
            firstLineIndent=0,
            bulletIndent=0,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=2,
        ),
    }


def _section(story: list, styles: dict[str, ParagraphStyle], en_title: str, ar_title: str, content: str, is_rtl: bool) -> None:
    if not content:
        return
    story.append(Paragraph(_shape(ar_title if is_rtl else en_title, is_rtl), styles["Section"]))
    story.append(Paragraph(_shape(content, is_rtl), styles["Body"]))


def _list_section(
    story: list,
    styles: dict[str, ParagraphStyle],
    en_title: str,
    ar_title: str,
    items: list[str],
    is_rtl: bool,
    inline: bool = False,
) -> None:
    clean_items = [item for item in items if item]
    if not clean_items:
        return
    story.append(Paragraph(_shape(ar_title if is_rtl else en_title, is_rtl), styles["Section"]))
    if inline:
        story.append(Paragraph(_shape(" • ".join(clean_items), is_rtl), styles["Body"]))
        return
    for item in clean_items:
        _bullet(story, styles, item, is_rtl)


def _experience_section(
    story: list,
    styles: dict[str, ParagraphStyle],
    en_title: str,
    ar_title: str,
    items: list[ExperienceItem],
    is_rtl: bool,
) -> None:
    clean_items = [item for item in items if item.title or item.company or item.bullets]
    if not clean_items:
        return
    story.append(Paragraph(_shape(ar_title if is_rtl else en_title, is_rtl), styles["Section"]))
    for item in clean_items:
        heading = _join_nonempty([item.title, item.company], " - ")
        meta = _join_nonempty([item.location, item.dates], " | ")
        if heading:
            story.append(Paragraph(_bold(heading, is_rtl), styles["Body"]))
        if meta:
            story.append(Paragraph(_shape(meta, is_rtl), styles["Contact"]))
        for bullet in item.bullets:
            _bullet(story, styles, bullet, is_rtl)


def _projects_section(story: list, styles: dict[str, ParagraphStyle], en_title: str, ar_title: str, items: list[ProjectItem], is_rtl: bool) -> None:
    clean_items = [item for item in items if item.name or item.bullets]
    if not clean_items:
        return
    story.append(Paragraph(_shape(ar_title if is_rtl else en_title, is_rtl), styles["Section"]))
    for item in clean_items:
        title = item.name
        if item.technologies:
            title = f"{title} | {', '.join(item.technologies)}" if title else ", ".join(item.technologies)
        if title:
            story.append(Paragraph(_bold(title, is_rtl), styles["Body"]))
        for bullet in item.bullets:
            _bullet(story, styles, bullet, is_rtl)


def _education_section(story: list, styles: dict[str, ParagraphStyle], en_title: str, ar_title: str, items: list[EducationItem], is_rtl: bool) -> None:
    clean_items = [item for item in items if item.degree or item.institution or item.notes]
    if not clean_items:
        return
    story.append(Paragraph(_shape(ar_title if is_rtl else en_title, is_rtl), styles["Section"]))
    for item in clean_items:
        heading = _join_nonempty([item.degree, item.institution], " - ")
        meta = _join_nonempty([item.location, item.dates], " | ")
        if heading:
            story.append(Paragraph(_bold(heading, is_rtl), styles["Body"]))
        if meta:
            story.append(Paragraph(_shape(meta, is_rtl), styles["Contact"]))
        for note in item.notes:
            _bullet(story, styles, note, is_rtl)


def _bullet(story: list, styles: dict[str, ParagraphStyle], text: str, is_rtl: bool) -> None:
    bullet = "•"
    story.append(Paragraph(_shape(text, is_rtl), styles["Bullet"], bulletText=bullet))


def _register_unicode_font() -> str:
    if ARABIC_FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return ARABIC_FONT_NAME
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            pdfmetrics.registerFont(TTFont(ARABIC_FONT_NAME, str(candidate)))
            return ARABIC_FONT_NAME
    return FONT_NAME


def _shape(text: str, is_rtl: bool, already_escaped: bool = False) -> str:
    value = text if already_escaped else _escape(text)
    if is_rtl and _has_arabic(value):
        return get_display(arabic_reshaper.reshape(value))
    return value


def _bold(text: str, is_rtl: bool) -> str:
    shaped = _shape(text, is_rtl)
    return shaped if is_rtl else f"<b>{shaped}</b>"


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _has_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06ff]", text))


def _join_nonempty(parts: list[str], separator: str) -> str:
    return separator.join(part.strip() for part in parts if part and part.strip())
