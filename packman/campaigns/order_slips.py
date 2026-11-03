"""Draw printable slips directly into a PDF; database selection happens in report_data."""

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import BinaryIO

from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Group
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from svglib.svglib import svg2rlg


@dataclass(frozen=True)
class SlipItem:
    category: str
    name: str
    quantity: int
    total: Decimal


@dataclass(frozen=True)
class SlipOrder:
    customer: str
    address: tuple[str, ...]
    paid: bool
    donation: Decimal
    total: Decimal
    items: tuple[SlipItem, ...]


@dataclass(frozen=True)
class SlipSeller:
    name: str
    signature: str
    den: str
    campaign: str
    eligible_count: int
    eligible_total: Decimal
    orders: tuple[SlipOrder, ...]
    award_text: str = ""


# ReportLab uses points (72 per inch), with (0, 0) at the bottom-left.
# Each Letter sheet has two vertical slots; each slip folds horizontally.
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 18
GUTTER = 18
SLIP_WIDTH = (PAGE_WIDTH - 2 * MARGIN - GUTTER) / 2
SLIP_HEIGHT = PAGE_HEIGHT - 2 * MARGIN
THANK_YOU_HEIGHT = 218
RECEIPT_HEIGHT = SLIP_HEIGHT - THANK_YOU_HEIGHT
PADDING = 12
CONTENT_WIDTH = SLIP_WIDTH - 2 * PADDING
ASSET_DIR = Path(__file__).parent / "static"
FONT_DIR = Path(__file__).parent / "pdf_assets"
FONT_FILES = (
    ("Slip", FONT_DIR / "PTSans-Regular.ttf"),
    ("SlipBold", FONT_DIR / "PTSans-Bold.ttf"),
    ("SlipWriting", FONT_DIR / "Kalam-Regular.ttf"),
)
LOGO_PATH = ASSET_DIR / "img" / "cub-scouts.svg"
PAID_STAMP_PATH = ASSET_DIR / "img" / "paid_stamp.svg"


def money(amount: Decimal) -> str:
    return f"${amount:,.0f}" if amount == amount.to_integral_value() else f"${amount:,.2f}"


@lru_cache(maxsize=1)
def register_fonts() -> None:
    # These names are used by Paragraphs and canvas text. Registration is process-wide;
    # the cache avoids reloading files for each download, and used glyphs are embedded in the PDF.
    for name, path in FONT_FILES:
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily("Slip", normal="Slip", bold="SlipBold")


@lru_cache(maxsize=1)
def logo():
    # svg2rlg converts SVG paths into ReportLab drawing objects, preserving vector sharpness.
    drawing = svg2rlg(str(LOGO_PATH))
    if drawing is None:
        raise ValueError("Unable to load the order slip logo.")
    return drawing


@lru_cache(maxsize=1)
def paid_stamp():
    drawing = svg2rlg(str(PAID_STAMP_PATH))
    if drawing is None:
        raise ValueError("Unable to load the paid order slip stamp.")
    pending = [drawing]
    # SVGs contain nested groups. Recolor every painted shape, leaving transparent areas alone.
    while pending:
        shape = pending.pop()
        for attribute in ("fillColor", "strokeColor"):
            color = getattr(shape, attribute, None)
            if color is not None:
                setattr(shape, attribute, colors.white if color == colors.white else colors.black)
        if isinstance(shape, Group):
            pending.extend(shape.contents)
    return drawing


def paragraph(text: str, size=10, bold=False, centered=False, font=None) -> Paragraph:
    # Paragraph supports a small markup language and wraps text; escape data before adding markup.
    return Paragraph(
        escape(text).replace("\n", "<br/>"),
        ParagraphStyle(
            "slip",
            fontName=font or ("SlipBold" if bold else "Slip"),
            fontSize=size,
            leading=size * 1.2,
            alignment=TA_CENTER if centered else TA_LEFT,
            textColor=colors.black,
        ),
    )


def draw_paragraph(canvas: Canvas, content: Paragraph, x: float, top: float, width: float) -> float:
    # wrap() measures without drawing. drawOn() expects a bottom-left position,
    # so subtract the measured height to lay out blocks downward from a top edge.
    height = content.wrap(width, PAGE_HEIGHT)[1]
    bottom = top - height
    content.drawOn(canvas, x, bottom)
    return bottom


def draw_thank_you_artwork(canvas: Canvas) -> None:
    canvas.beginForm("thank-you", 0, 0, SLIP_WIDTH, THANK_YOU_HEIGHT)

    # Everything except the two name lines is shared artwork with fixed positions.
    top = THANK_YOU_HEIGHT - PADDING
    for text, size, bold in (
        (_("Thank You!"), 30, True),
        (_("For Supporting"), 17, False),
        (_("Cub Scout Pack 144"), 19, True),
    ):
        top = draw_paragraph(canvas, paragraph(text, size, bold, True), PADDING, top, CONTENT_WIDTH) - 2

    # Draw the logo image below the thank-you text.
    image_size = 88
    canvas.saveState()
    canvas.translate(PADDING, top - image_size - 8)
    canvas.doForm("slip-logo")
    canvas.restoreState()

    # Draw the signature block to the right of the logo.
    signature_x = PADDING + image_size + 12
    signature_width = SLIP_WIDTH - PADDING - signature_x
    signature_top = top - 14
    draw_paragraph(
        canvas, paragraph(_("Thanks,"), 23, font="SlipWriting"), signature_x, signature_top, signature_width
    )
    canvas.setLineWidth(1)
    canvas.line(signature_x, 45.2, signature_x + signature_width, 45.2)
    draw_paragraph(canvas, paragraph("pack144.org", 10), signature_x, 37.2, signature_width)

    canvas.endForm()


def draw_thanks(canvas: Canvas, seller: SlipSeller) -> None:
    canvas.saveState()

    # Moving the origin to the top-right and rotating isolates the upside-down
    # thank-you side. Names are single-line text and never affect the fold or artwork.
    canvas.translate(SLIP_WIDTH, SLIP_HEIGHT)
    canvas.rotate(180)
    canvas.doForm("thank-you")
    canvas.setFillColor(colors.black)
    canvas.setFont("SlipWriting", 25)
    canvas.drawString(PADDING + 100, 54.2, seller.signature)
    canvas.setFont("Slip", 8)
    canvas.drawCentredString(SLIP_WIDTH / 2, PADDING + 1.6, f"{seller.name} • {seller.den}")

    canvas.restoreState()


def order_header(order: SlipOrder) -> Paragraph:
    content = [f"<b>{escape(order.customer)}</b>"] + [escape(line) for line in order.address]
    return Paragraph(
        "<br/>".join(content),
        ParagraphStyle(
            "customer",
            fontName="Slip",
            fontSize=11,
            leading=13.2,
        ),
    )


def item_table(order: SlipOrder, compact: bool = False, compact_padding: float = 1) -> Table:
    # Category rows span all columns; ordinary rows keep quantity/name/amount separate.
    rows = [[paragraph(_("Qty"), 9, True), paragraph(_("Product"), 9, True), paragraph(_("Amount"), 9, True)]]
    category_rows = []
    previous_category = None
    for item in order.items:
        description = escape(item.name)
        if item.category != previous_category:
            category_rows.append(len(rows))
            rows.append([paragraph(item.category, 10, True), "", ""])
        previous_category = item.category
        rows.append(
            [
                str(item.quantity),
                Paragraph(description, ParagraphStyle("product", fontName="Slip", fontSize=9, leading=11)),
                money(item.total),
            ]
        )
    quantity_width = max(27, *(pdfmetrics.stringWidth(str(item.quantity), "Slip", 9) + 6 for item in order.items))
    amount_width = max(54, *(pdfmetrics.stringWidth(money(item.total), "Slip", 9) + 6 for item in order.items))
    table = Table(
        rows, colWidths=[quantity_width, CONTENT_WIDTH - quantity_width - amount_width, amount_width], repeatRows=1
    )
    # TableStyle commands use (column, row) coordinates; -1 means the final column/row.
    # repeatRows=1 repeats the column headings on each continuation fragment.
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Slip"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), compact_padding if compact else 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), compact_padding if compact else 4),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.gray),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ]
        )
    )
    for row in category_rows:
        # NOSPLIT keeps a category heading with its first product when Table.split() paginates.
        table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, row), (-1, row)),
                    ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#dddddd")),
                    ("LINEABOVE", (0, row), (-1, row), 0.75, colors.gray),
                    ("TOPPADDING", (0, row), (-1, row), 2 if compact else 5),
                    ("BOTTOMPADDING", (0, row), (-1, row), 2 if compact else 5),
                    ("NOSPLIT", (0, row), (-1, row + 1)),
                ]
            )
        )
    return table


def table_top(order: SlipOrder, receipt_height: float, label: str = "") -> float:
    # Shared measurement keeps fit checks and actual drawing consistent.
    # Single slips need only a 6 pt gap; continuations also need their numbered label.
    header_height = order_header(order).wrap(CONTENT_WIDTH, receipt_height)[1]
    top = receipt_height - PADDING - header_height - 6
    if label:
        top -= paragraph(label, 8).wrap(CONTENT_WIDTH, receipt_height)[1]
        if order.address:
            top -= 12
    return top


def split_order(order: SlipOrder, receipt_height: float = RECEIPT_HEIGHT) -> list[Table]:
    # Stop products 6 pt above the rule at y=60, reserving another 20 pt for a donation.
    bottom = 66 + (20 if order.donation else 0)
    available = table_top(order, receipt_height) - bottom
    remaining = item_table(order)

    # Try one slip with normal, compact, then slightly tighter padding. Fonts never change.
    if remaining.wrap(CONTENT_WIDTH, available)[1] > available:
        remaining = item_table(order, compact=True)
    if remaining.wrap(CONTENT_WIDTH, available)[1] > available:
        remaining = item_table(order, compact=True, compact_padding=0.75)
    if remaining.wrap(CONTENT_WIDTH, available)[1] <= available:
        return [remaining]

    # Once splitting is unavoidable, restore normal spacing for readability.
    # Use the maximum possible part number to conservatively measure the label;
    # the real label is drawn later, when the final fragment count is known.
    label = _("Order slip %(part)s of %(count)s") % {"part": len(order.items), "count": len(order.items)}
    available = table_top(order, receipt_height, label) - bottom
    remaining = item_table(order)
    parts = []
    while True:
        height = remaining.wrap(CONTENT_WIDTH, available)[1]
        if height <= available:
            parts.append(remaining)
            return parts
        fragments = remaining.split(CONTENT_WIDTH, available)
        # split() returns the fitting fragment plus the remaining table, respecting
        # repeated headings and NOSPLIT. An unsplittable tall row is an explicit error.
        if len(fragments) != 2:
            raise ValueError("An order slip item cannot fit in the printable area.")
        parts.append(fragments[0])
        remaining = fragments[1]


def draw_horizontal_rule(canvas: Canvas, x: float, y: float, width: float, dashed: bool = False) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.gray)
    canvas.setLineWidth(0.5)
    if dashed:
        canvas.setDash(3, 3)
    else:
        canvas.setDash()
    canvas.line(x, y, x + width, y)
    canvas.restoreState()


def draw_receipt(
    canvas: Canvas, order: SlipOrder, table: Table, part: int, count: int, receipt_height: float = RECEIPT_HEIGHT
) -> None:
    header_bottom = draw_paragraph(canvas, order_header(order), PADDING, receipt_height - PADDING, CONTENT_WIDTH)
    label = _("Order slip %(part)s of %(count)s") % {"part": part, "count": count} if count > 1 else ""
    if label:
        draw_paragraph(canvas, paragraph(label, 8), PADDING, header_bottom - 6, CONTENT_WIDTH)
    top = table_top(order, receipt_height, label)
    height = table.wrap(CONTENT_WIDTH, receipt_height)[1]
    table.drawOn(canvas, PADDING, top - height)

    draw_horizontal_rule(canvas, PADDING, 60, CONTENT_WIDTH)
    top = 52
    if part != count:
        # Show the order's donation and payment total only on its final fragment.
        draw_paragraph(
            canvas,
            paragraph(_("Continued on the next slip. Total shown on the final slip."), 10),
            PADDING,
            top,
            CONTENT_WIDTH,
        )
        return
    if order.donation:
        canvas.setFillColor(colors.black)
        canvas.setFont("Slip", 10)
        canvas.drawRightString(SLIP_WIDTH - PADDING, 68, _("Donation: %(amount)s") % {"amount": money(order.donation)})
    total = _("Total: %(amount)s") % {"amount": money(order.total)}
    cod = "" if order.paid else _("COD — Please Pay")
    summary = f"{cod}   {total}" if cod else total
    # Measure both labels together to ensure the left COD and right total cannot overlap.
    size = 13 if order.paid else 11
    while pdfmetrics.stringWidth(summary, "SlipBold", size) > CONTENT_WIDTH and size > 9:
        size -= 1
    if pdfmetrics.stringWidth(summary, "SlipBold", size) > CONTENT_WIDTH:
        raise ValueError("An order slip total cannot fit in the printable area.")
    canvas.setFillColor(colors.black)
    canvas.setFont("SlipBold", size)
    canvas.drawRightString(SLIP_WIDTH - PADDING, 24, total)
    if cod:
        canvas.drawString(PADDING, 24, cod)
    if order.paid:
        # Draw the reusable 54 pt stamp at 36 pt, centered over the numeric amount.
        # Drawing it after the text overlays it rather than reserving a separate column.
        amount_width = pdfmetrics.stringWidth(money(order.total), "SlipBold", size)
        canvas.saveState()
        canvas.translate(SLIP_WIDTH - PADDING - amount_width / 2 - 18, 14)
        canvas.scale(2 / 3, 2 / 3)
        canvas.doForm("paid-stamp")
        canvas.restoreState()


def draw_slip(
    canvas: Canvas,
    seller: SlipSeller,
    order: SlipOrder,
    table: Table,
    part: int,
    count: int,
    x: float,
) -> None:
    # Save the current canvas state and move the origin to the slot's bottom-left corner.
    canvas.saveState()
    canvas.translate(x, MARGIN)

    draw_thanks(canvas, seller)
    draw_receipt(canvas, order, table, part, count)

    # Draw a horizontal line separating the receipt from the summary
    draw_horizontal_rule(canvas, 0, RECEIPT_HEIGHT, SLIP_WIDTH, dashed=True)

    # Restore the canvas state to undo the translation and any other modifications.
    canvas.restoreState()


def draw_seller_summary(canvas: Canvas, seller: SlipSeller) -> None:
    # This occupies only the left slot, not a whole page. The first slip is drawn beside it.
    canvas.saveState()
    canvas.translate(MARGIN, 0)
    top = PAGE_HEIGHT - 180

    # Collect text blocks to render
    lines = [
        (seller.name, 30, True),
        (seller.den, 20, False),
        (seller.campaign, 16, False),
        (
            ngettext("%(count)s eligible order", "%(count)s eligible orders", seller.eligible_count)
            % {"count": seller.eligible_count},
            14,
            False,
        ),
        (_("%(amount)s Eligible Total Sales") % {"amount": money(seller.eligible_total)}, 16, True),
    ]
    # Append the award (e.g. "Made Gold!") text line if it exists
    if seller.award_text:
        lines.append((seller.award_text, 20, True))

    # Draw separate text blocks with their own font sizes and bold settings, leaving 18 points between blocks.
    for text, size, bold in lines:
        top = draw_paragraph(canvas, paragraph(text, size, bold, True), PADDING, top, CONTENT_WIDTH) - 18
    canvas.restoreState()


def finish_sheet(canvas: Canvas) -> None:
    canvas.setStrokeColor(colors.gray)
    canvas.setDash(2, 4)
    canvas.line(PAGE_WIDTH / 2, MARGIN, PAGE_WIDTH / 2, PAGE_HEIGHT - MARGIN)
    canvas.showPage()


def define_svg_form(canvas: Canvas, name: str, drawing: Drawing, size: float) -> None:
    # A PDF form is reusable artwork, not an input form. Define it once and
    # place it with doForm() on every slip to avoid duplicating SVG paths.
    canvas.beginForm(name, 0, 0, size, size)
    canvas.scale(size / drawing.width, size / drawing.height)
    renderPDF.draw(drawing, canvas, 0, 0)
    canvas.endForm()


def draw_seller_slips(canvas: Canvas, seller: SlipSeller) -> None:
    # Slots are full-height columns: 0 is left, 1 is right.
    # The first sheet uses slot 0 for the summary and slot 1 for a slip; later sheets use both for slips.

    # Draw the cub summary in the left slot of the first sheet
    draw_seller_summary(canvas, seller)
    slot = 1

    # Draw each order slip in the appropriate slot, creating new sheets as needed
    for order in seller.orders:
        parts = split_order(order)
        for part, table in enumerate(parts, 1):
            # Draw this order fragment in the current slot.
            draw_slip(canvas, seller, order, table, part, len(parts), MARGIN + slot * (SLIP_WIDTH + GUTTER))
            slot += 1

            # If we've filled both slots, finish the current sheet and start a new one
            if slot == 2:
                finish_sheet(canvas)
                slot = 0

    # Finish a partially used sheet before starting another cub; never mix cubs.
    if slot == 1:
        finish_sheet(canvas)


def render_order_slips(sellers: tuple[SlipSeller, ...], output: BinaryIO) -> None:
    # Register fonts before rendering any order slips
    register_fonts()

    # Set up a new PDF canvas for the order slips
    canvas = Canvas(output, pagesize=letter, pageCompression=1)
    canvas.setTitle(_("Order Slips"))
    canvas.setAuthor("Cub Scout Pack 144")

    # Define reusable SVG forms for the order slips
    draw_thank_you_artwork(canvas)
    define_svg_form(canvas, "slip-logo", logo(), 88)
    define_svg_form(canvas, "paid-stamp", paid_stamp(), 54)

    # Draw the order slips for each seller
    for seller in sellers:
        draw_seller_slips(canvas, seller)

    # Finalize the PDF after all sellers' slips have been drawn
    canvas.save()
