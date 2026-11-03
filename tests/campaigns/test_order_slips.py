from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase

from pypdf import PdfReader
from reportlab.graphics.shapes import Group
from reportlab.lib import colors

from packman.campaigns.order_slips import (
    CONTENT_WIDTH,
    PADDING,
    RECEIPT_HEIGHT,
    SlipItem,
    SlipOrder,
    SlipSeller,
    draw_receipt,
    draw_thanks,
    item_table,
    order_header,
    paid_stamp,
    register_fonts,
    render_order_slips,
    split_order,
)


class OrderSlipPDFTestCase(SimpleTestCase):
    def setUp(self):
        register_fonts()
        self.order = SlipOrder(
            customer="Sample Customer",
            address=("123 Example Street", "Seattle, WA, 98101"),
            paid=False,
            donation=Decimal("5.25"),
            total=Decimal("35.75"),
            items=(SlipItem("Popcorn", "Caramel Corn", 2, Decimal("30.50")),),
        )
        self.seller = SlipSeller(
            name="Alex Example",
            signature="Alex",
            den="Den 2",
            campaign="2026 Campaign",
            eligible_count=1,
            eligible_total=Decimal("35.75"),
            orders=(self.order,),
        )

    def render(self, sellers):
        output = BytesIO()
        render_order_slips(sellers, output)
        output.seek(0)
        return PdfReader(output)

    def test_thank_you_half_has_logo_and_rotated_handwriting_signature(self):
        reader = self.render((self.seller,))
        text = reader.pages[0].extract_text()
        for value in ("Thank You!", "For Supporting", "Cub Scout Pack 144", "Thanks,", "Alex", "pack144.org"):
            self.assertIn(value, text)
        fonts = reader.pages[0]["/Resources"]["/Font"].get_object()
        self.assertTrue(any("Kalam" in font.get_object()["/BaseFont"] for font in fonts.values()))
        content = reader.pages[0].get_contents().get_data()
        self.assertIn(b"-1 0 0 -1", content)
        shared = reader.pages[0]["/Resources"]["/XObject"]["/FormXob.thank-you"].get_object()
        artwork = shared["/Resources"]["/XObject"]["/FormXob.slip-logo"].get_object()
        self.assertTrue(artwork.get_data())

    def test_two_orders_per_page_and_odd_groups_do_not_mix_sellers(self):
        first = replace(self.seller, orders=(self.order,) * 3)
        second_order = replace(self.order, customer="Second Seller Customer")
        second = replace(self.seller, name="Sam Example", orders=(second_order,))
        reader = self.render((first, second))
        self.assertEqual(len(reader.pages), 3)
        self.assertEqual(reader.pages[0].extract_text().count("Sample Customer"), 1)
        self.assertEqual(reader.pages[1].extract_text().count("Sample Customer"), 2)
        self.assertEqual(reader.pages[2].extract_text().count("Sample Customer"), 0)
        self.assertNotIn("Second Seller Customer", reader.pages[1].extract_text())
        self.assertIn("Sam Example", reader.pages[2].extract_text())
        self.assertIn("Second Seller Customer", reader.pages[2].extract_text())
        for page in reader.pages:
            self.assertEqual(tuple(page.mediabox), (0, 0, 612, 792))

    def test_summary_uses_left_slot_and_first_order_uses_right_slot(self):
        reader = self.render((self.seller,))
        self.assertEqual(len(reader.pages), 1)
        positions = []
        reader.pages[0].extract_text(
            visitor_text=lambda text, cm, tm, font, size: positions.append((text, cm[4] + tm[4]))
        )
        customer_x = next(x for text, x in positions if "Sample Customer" in text)
        self.assertGreater(customer_x, 306)

    def test_separator_prints_supplied_award_text(self):
        seller = replace(self.seller, award_text="Sample Recognition")
        reader = self.render((seller,))
        self.assertIn("Sample Recognition", reader.pages[0].extract_text())
        reader = self.render((self.seller,))
        self.assertNotIn("Sample Recognition", reader.pages[0].extract_text())

    def test_long_order_continues_without_losing_items_or_repeating_total(self):
        items = tuple(SlipItem("Snacks", f"Product number {index:02}", 1, Decimal("1.00")) for index in range(40))
        order = replace(self.order, items=items, total=Decimal("45.25"))
        parts = split_order(order)
        self.assertGreater(len(parts), 1)
        for table in parts:
            self.assertEqual(table._cellStyles[0][0].topPadding, 4)
        reader = self.render((replace(self.seller, orders=(order,)),))
        text = "\n".join(page.extract_text() for page in reader.pages)
        for index in range(40):
            self.assertEqual(text.count(f"Product number {index:02}"), 1)
        self.assertEqual(text.count("Total: $45.25"), 1)
        self.assertEqual(text.count("Donation: $5.25"), 1)
        self.assertIn(f"Order slip 1 of {len(parts)}", text)
        self.assertIn(f"Order slip {len(parts)} of {len(parts)}", text)

    def test_categories_have_separate_rows_and_stay_with_their_first_product(self):
        order = replace(
            self.order,
            items=tuple(SlipItem(f"Category {index}", f"Product {index}", 1, Decimal("1")) for index in range(30)),
        )
        reader = self.render((replace(self.seller, orders=(order,)),))
        for page in reader.pages:
            lines = [line.strip() for line in page.extract_text().splitlines() if line.strip()]
            for index, line in enumerate(lines):
                if line.startswith("Category "):
                    number = line.removeprefix("Category ")
                    self.assertIn(f"Product {number}", lines[index + 1 :])

    def test_normal_spacing_is_preserved_when_order_fits(self):
        table = split_order(self.order)[0]
        self.assertEqual(table._cellStyles[2][0].topPadding, 4)
        self.assertEqual(table._cellStyles[2][0].bottomPadding, 4)

    def test_pdf_fonts_are_not_public_static_files(self):
        for filename in ("PTSans-Regular.ttf", "PTSans-Bold.ttf", "Kalam-Regular.ttf"):
            self.assertIsNone(finders.find(f"fonts/{filename}"))

    def test_borderline_order_uses_actual_single_slip_space_and_quarter_point_reduction(self):
        order = replace(
            self.order,
            items=tuple(
                SlipItem(f"Category {index // 4}", f"Product {index}", 1, Decimal("1")) for index in range(21)
            ),
        )
        compact_height = item_table(order, compact=True).wrap(CONTENT_WIDTH, RECEIPT_HEIGHT)[1]
        # Make the available single-slip space two points smaller than the compact table.
        header_height = order_header(order).wrap(CONTENT_WIDTH, RECEIPT_HEIGHT)[1]
        receipt_height = compact_height - 2 + PADDING + header_height + 6 + 86
        parts = split_order(order, receipt_height)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]._cellStyles[2][0].topPadding, 0.75)
        self.assertLessEqual(parts[0].wrap(CONTENT_WIDTH, receipt_height)[1], compact_height - 2)

    def test_tight_rows_are_used_before_creating_continuations(self):
        order = replace(
            self.order, items=tuple(SlipItem("Snacks", f"Product {index}", 1, Decimal("1")) for index in range(24))
        )
        normal_height = item_table(order).wrap(CONTENT_WIDTH, RECEIPT_HEIGHT)[1]
        header_height = order_header(order).wrap(CONTENT_WIDTH, RECEIPT_HEIGHT)[1]
        available = RECEIPT_HEIGHT - 2 * PADDING - header_height - 24 - 58 - 20
        self.assertGreater(normal_height, available)
        parts = split_order(order)
        self.assertEqual(len(parts), 1)
        self.assertLessEqual(parts[0].wrap(CONTENT_WIDTH, RECEIPT_HEIGHT)[1], available)
        self.assertEqual(parts[0]._cellStyles[2][0].topPadding, 1)

    def test_long_unicode_names_and_markup_are_literal_text(self):
        order = replace(
            self.order,
            customer="Zoë <Example> & José",
            address=("A long street address " * 4, "Seattle, WA, 98101"),
            items=(SlipItem("Nuts & Snacks", "Extra long product title " * 4, 1, Decimal("30.50")),),
        )
        reader = self.render((replace(self.seller, orders=(order,)),))
        text = "\n".join(page.extract_text() for page in reader.pages)
        self.assertIn("Zoë <Example> & José", text)
        self.assertIn("Nuts & Snacks", text)
        self.assertIn("$35.75", text)

    def test_paid_and_donation_free_summary(self):
        order = replace(self.order, paid=True, donation=Decimal("0"), total=Decimal("30.50"))
        reader = self.render((replace(self.seller, orders=(order,)),))
        text = reader.pages[0].extract_text()
        self.assertNotIn("PAID", text)
        artwork = reader.pages[0]["/Resources"]["/XObject"]["/FormXob.paid-stamp"].get_object()
        self.assertTrue(artwork.get_data())
        self.assertIn("Total: $30.50", text)
        self.assertNotIn("COD", text)
        self.assertNotIn("Donation:", text)

    def test_cod_is_left_aligned_on_same_line_as_right_aligned_total(self):
        with patch("packman.campaigns.order_slips.Canvas") as canvas_class:
            canvas = canvas_class.return_value
            with patch("packman.campaigns.order_slips.draw_paragraph") as draw_text:
                draw_text.side_effect = lambda canvas, text, x, top, width: top - text.wrap(width, 792)[1]
                draw_receipt(canvas, self.order, split_order(self.order)[0], 1, 1)
        x, y, text = canvas.drawRightString.call_args.args
        self.assertEqual(x, PADDING + CONTENT_WIDTH)
        self.assertEqual(y, 24)
        self.assertEqual(text, "Total: $35.75")
        canvas.drawString.assert_any_call(PADDING, 24, "COD — Please Pay")
        canvas.drawRightString.assert_any_call(PADDING + CONTENT_WIDTH, 68, "Donation: $5.25")
        canvas.line.assert_any_call(PADDING, 60, PADDING + CONTENT_WIDTH, 60)

    def test_single_slips_have_tight_header_spacing_and_continuations_keep_label_space(self):
        for address, count in (((), 1), (self.order.address, 1), (self.order.address, 2)):
            with self.subTest(address=address, count=count):
                order = replace(self.order, address=address)
                table = split_order(order)[0]
                with patch.object(table, "drawOn") as draw_table:
                    with patch("packman.campaigns.order_slips.Canvas") as canvas_class:
                        draw_receipt(canvas_class.return_value, order, table, 1, count)
                table_top = draw_table.call_args.args[2] + table.wrap(CONTENT_WIDTH, RECEIPT_HEIGHT)[1]
                name_bottom = RECEIPT_HEIGHT - PADDING - order_header(order).wrap(CONTENT_WIDTH, RECEIPT_HEIGHT)[1]
                self.assertAlmostEqual(name_bottom - table_top, 27.6 if count > 1 else 6)

    def test_paid_stamp_is_black_and_white(self):
        pending = [paid_stamp()]
        colored_shapes = 0
        while pending:
            shape = pending.pop()
            for attribute in ("fillColor", "strokeColor"):
                color = getattr(shape, attribute, None)
                if color is not None:
                    colored_shapes += 1
                    self.assertIn(color, (colors.black, colors.white))
            if isinstance(shape, Group):
                pending.extend(shape.contents)
        self.assertGreater(colored_shapes, 0)

    def test_paid_stamp_is_small_and_overlaid_on_the_amount(self):
        order = replace(self.order, paid=True)
        with patch("packman.campaigns.order_slips.Canvas") as canvas_class:
            canvas = canvas_class.return_value
            draw_receipt(canvas, order, split_order(order)[0], 1, 1)
        canvas.scale.assert_called_with(2 / 3, 2 / 3)
        canvas.doForm.assert_called_once_with("paid-stamp")
        stamp_x, stamp_y = canvas.translate.call_args.args
        self.assertGreater(stamp_x, CONTENT_WIDTH - 80)
        self.assertEqual(stamp_y, 14)
        calls = canvas.method_calls
        total_call = next(
            index for index, call in enumerate(calls) if call[0] == "drawRightString" and call[1][1] == 24
        )
        stamp_call = next(index for index, call in enumerate(calls) if call[0] == "doForm")
        self.assertGreater(stamp_call, total_call)

    def test_empty_report_is_a_readable_pdf(self):
        reader = self.render(())
        self.assertEqual(len(reader.pages), 1)
        self.assertIn("No product orders to print.", reader.pages[0].extract_text())

    def test_different_names_do_not_change_thank_you_positions(self):
        sellers = (self.seller, replace(self.seller, signature="Alexandria", name="Alexandria Example", den="Den 10"))
        calls = []
        for seller in sellers:
            with patch("packman.campaigns.order_slips.Canvas") as canvas_class:
                canvas = canvas_class.return_value
                draw_thanks(canvas, seller)
                calls.append(
                    (
                        canvas.translate.call_args,
                        canvas.drawString.call_args.args[:2],
                        canvas.drawCentredString.call_args.args[:2],
                    )
                )
                canvas.doForm.assert_called_once_with("thank-you")
                canvas.setFont.assert_any_call("SlipWriting", 25)
        self.assertEqual(calls[0], calls[1])
