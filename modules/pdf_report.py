from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from bidi.algorithm import get_display
import arabic_reshaper
import os
from datetime import datetime

FONT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "fonts",
    "Cairo-Regular.ttf"
)

pdfmetrics.registerFont(TTFont("ArabicFont", FONT_PATH))
FONT_NAME = "ArabicFont"

def ar(text):
    text = "" if text is None else str(text)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def draw_rtl(c, text, x, y, size=11, color=colors.black):
    c.setFillColor(color)
    c.setFont(FONT_NAME, size)
    c.drawRightString(x, y, ar(text))

def draw_wrapped_rtl(c, text, x, y, max_width, line_height=16, size=10, color=colors.black):
    words = str(text).split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        test_width = c.stringWidth(ar(test_line), FONT_NAME, size)

        if test_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        draw_rtl(c, line, x, y, size, color)
        y -= line_height

    return y


def draw_ltr(c, text, x, y, size=11, color=colors.black):
    c.setFillColor(color)
    c.setFont(FONT_NAME, size)
    c.drawString(x, y, str(text))


def short_text(text, length=95):
    text = "" if text is None else str(text)
    return text[:length] + "..." if len(text) > length else text


def get_level(percentage):
    if percentage >= 90:
        return "ممتاز جدًا"
    elif percentage >= 75:
        return "جيد جدًا"
    elif percentage >= 60:
        return "جيد"
    else:
        return "يحتاج إلى مراجعة"


def get_recommendation(percentage):
    if percentage >= 90:
        return "أداء ممتاز، استمر على هذا المستوى."
    elif percentage >= 75:
        return "أداء جيد جدًا، يوصى بمراجعة الأخطاء البسيطة."
    elif percentage >= 60:
        return "الأداء جيد، لكن يحتاج إلى مراجعة بعض المفاهيم."
    else:
        return "ينصح بإعادة دراسة المحتوى ثم إعادة الاختبار."


def draw_footer(c, page_number, width):
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.line(45, 45, width - 45, 45)

    draw_rtl(
        c,
        "تم إنشاء هذا التقرير تلقائيًا بواسطة نظام AI Edu Generator",
        width - 45,
        28,
        8,
        colors.HexColor("#64748B")
    )

    draw_ltr(
        c,
        f"Page {page_number}",
        45,
        28,
        8,
        colors.HexColor("#64748B")
    )


def new_page(c, page_number, width, height):
    draw_footer(c, page_number, width)
    c.showPage()
    return height - 60


def generate_pdf(result, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    margin = 45
    y = height - 50
    page_number = 1

    score = result["score"]
    total = result["total"]
    percentage = result["percentage"]
    correct_count = score
    wrong_count = total - score
    level = get_level(percentage)
    recommendation = get_recommendation(percentage)
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Header
    c.setFillColor(colors.HexColor("#2563EB"))
    c.roundRect(margin, y - 85, width - 2 * margin, 85, 16, fill=1, stroke=0)

    draw_rtl(c, "تقرير نتيجة الاختبار", width - margin - 25, y - 32, 22, colors.white)
    draw_rtl(c, "AI Edu Generator", width - margin - 25, y - 58, 13, colors.white)
    draw_rtl(c, "نظام ذكي لتوليد وتصحيح الأسئلة التعليمية", width - margin - 25, y - 77, 10, colors.white)

    y -= 125

    # Summary title
    draw_rtl(c, "معلومات الاختبار", width - margin, y, 16, colors.HexColor("#0F172A"))
    y -= 25

    # Summary box
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.roundRect(margin, y - 115, width - 2 * margin, 115, 14, fill=1, stroke=1)

    draw_rtl(c, f"تاريخ التقرير: {date_now}", width - margin - 20, y - 25, 11)
    draw_rtl(c, f"عدد الأسئلة: {total}", width - margin - 20, y - 50, 11)
    draw_rtl(c, f"التقييم: {level}", width - margin - 20, y - 75, 12, colors.HexColor("#14B8A6"))
    draw_rtl(c, f"التوصية: {recommendation}", width - margin - 20, y - 100, 10)

    y -= 145

    # Stat cards
    card_w = (width - 2 * margin - 30) / 4
    card_h = 70
    stats = [
        ("الدرجة", f"{score} / {total}", "#2563EB"),
        ("النسبة", f"{percentage}%", "#14B8A6"),
        ("الصحيح", str(correct_count), "#16A34A"),
        ("الخطأ", str(wrong_count), "#DC2626"),
    ]

    x = margin
    for title, value, color in stats:
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.roundRect(x, y - card_h, card_w, card_h, 12, fill=1, stroke=1)

        draw_rtl(c, title, x + card_w - 12, y - 23, 10, colors.HexColor("#64748B"))
        draw_ltr(c, value, x + 18, y - 50, 16, colors.HexColor(color))

        x += card_w + 10

    y -= 105

    # Progress bar
    draw_rtl(c, "شريط نسبة النجاح", width - margin, y, 12, colors.HexColor("#0F172A"))
    y -= 20

    bar_x = margin
    bar_y = y - 12
    bar_w = width - 2 * margin
    bar_h = 14

    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.roundRect(bar_x, bar_y, bar_w, bar_h, 7, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#2563EB"))
    c.roundRect(bar_x, bar_y, bar_w * (percentage / 100), bar_h, 7, fill=1, stroke=0)

    y -= 50

    # Auto summary
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.roundRect(margin, y - 100, width - 2 * margin, 100, 14, fill=1, stroke=1)

    summary = (
        f"حصل الطالب على {score} من أصل {total} بنسبة {percentage}%، "
        f"ويصنف أداؤه ضمن مستوى {level}. {recommendation}"
    )

    draw_rtl(c, "ملخص الأداء", width - margin - 20, y - 22, 13, colors.HexColor("#2563EB"))
    draw_wrapped_rtl(
    c,
    summary,
    width - margin - 20,
    y - 50,
    width - 2 * margin - 40,
    line_height=16,
    size=10,
    color=colors.black
    ) 

    y -= 130

    # Details
    draw_rtl(c, "تفاصيل الأسئلة", width - margin, y, 16, colors.HexColor("#0F172A"))
    y -= 30

    for index, q in enumerate(result["results"], start=1):
        if y < 165:
            y = new_page(c, page_number, width, height)
            page_number += 1
            draw_rtl(c, "تفاصيل الأسئلة", width - margin, y, 16, colors.HexColor("#2563EB"))
            y -= 30

        is_correct = q["is_correct"]
        box_color = colors.HexColor("#DCFCE7") if is_correct else colors.HexColor("#FEE2E2")
        side_color = colors.HexColor("#16A34A") if is_correct else colors.HexColor("#DC2626")
        status = "صحيحة" if is_correct else "خاطئة"

        box_h = 125

        c.setFillColor(box_color)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.roundRect(margin, y - box_h, width - 2 * margin, box_h, 14, fill=1, stroke=1)

        c.setFillColor(side_color)
        c.rect(width - margin - 8, y - box_h, 8, box_h, fill=1, stroke=0)

        draw_rtl(c, f"السؤال {index} - {q['type']}", width - margin - 20, y - 22, 12, colors.HexColor("#0F172A"))

        draw_rtl(c, f"السؤال: {short_text(q['question'], 95)}", width - margin - 20, y - 47, 9)
        draw_rtl(c, f"إجابة الطالب: {short_text(q['user_answer'], 75)}", width - margin - 20, y - 72, 9)
        draw_rtl(c, f"الإجابة الصحيحة: {short_text(q['correct_answer'], 75)}", width - margin - 20, y - 97, 9)
        draw_rtl(c, f"الحالة: {status}", margin + 150, y - 97, 10, side_color)

        y -= box_h + 18

    # Final summary
    if y < 150:
        y = new_page(c, page_number, width, height)
        page_number += 1

    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.roundRect(margin, y - 105, width - 2 * margin, 105, 14, fill=1, stroke=1)

    draw_rtl(c, "الخلاصة النهائية", width - margin - 20, y - 25, 14, colors.HexColor("#2563EB"))
    draw_rtl(c, f"إجمالي الأسئلة: {total}", width - margin - 20, y - 50, 10)
    draw_rtl(c, f"الإجابات الصحيحة: {correct_count}", width - margin - 20, y - 70, 10, colors.HexColor("#16A34A"))
    draw_rtl(c, f"الإجابات الخاطئة: {wrong_count}", width / 2, y - 70, 10, colors.HexColor("#DC2626"))
    draw_rtl(c, f"التقييم النهائي: {level}", width - margin - 20, y - 90, 10, colors.HexColor("#14B8A6"))

    draw_footer(c, page_number, width)
    c.save()