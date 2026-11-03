from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase

from pypdf import PdfReader

from packman.campaigns.order_slips import (
    CONTENT_WIDTH,
    PADDING,
    RECEIPT_HEIGHT,
    SlipItem,
    SlipOrder,
    SlipSeller,
    draw_receipt,
    item_table,
    order_header,
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
        text = reader.pages[1].extract_text()
        for value in ("Thank You!", "For Supporting", "Cub Scout Pack 144", "Thanks,", "Alex", "pack144.org"):
            self.assertIn(value, text)
        self.assertIn("Alex • Den 2", text)
        fonts = reader.pages[1]["/Resources"]["/Font"].get_object()
        self.assertTrue(any("Kalam" in font.get_object()["/BaseFont"] for font in fonts.values()))
        content = reader.pages[1].get_contents().get_data()
        self.assertIn(b"-1 0 0 -1", content)
        shared = reader.pages[1]["/Resources"]["/XObject"]["/FormXob.thank-you"].get_object()
        artwork = shared["/Resources"]["/XObject"]["/FormXob.slip-logo"].get_object()
        self.assertTrue(artwork.get_data())

    def test_two_orders_per_page_and_odd_groups_do_not_mix_sellers(self):
        first = replace(self.seller, orders=(self.order,) * 3)
        second_order = replace(self.order, customer="Second Seller Customer")
        second = replace(self.seller, name="Sam Example", orders=(second_order,))
        reader = self.render((first, second))
        self.assertEqual(len(reader.pages), 4)
        self.assertEqual(reader.pages[1].extract_text().count("Sample Customer"), 1)
        self.assertEqual(reader.pages[2].extract_text().count("Sample Customer"), 2)
        self.assertEqual(reader.pages[3].extract_text().count("Sample Customer"), 0)
        self.assertNotIn("Second Seller Customer", reader.pages[2].extract_text())
        self.assertIn("Sam Example", reader.pages[3].extract_text())
        self.assertIn("Second Seller Customer", reader.pages[3].extract_text())
        self.assertNotIn(first.name, reader.pages[2].extract_text())
        for page in reader.pages:
            self.assertEqual(tuple(page.mediabox), (0, 0, 612, 792))

    def test_summary_uses_left_slot_and_first_order_uses_right_slot(self):
        reader = self.render((self.seller,))
        self.assertEqual(len(reader.pages), 2)
        positions = []
        reader.pages[1].extract_text(
            visitor_text=lambda text, cm, tm, font, size: positions.append((text, cm[4] + tm[4]))
        )
        customer_x = next(x for text, x in positions if "Sample Customer" in text)
        self.assertGreater(customer_x, 306)

    def test_summary_prints_supplied_award_text(self):
        seller = replace(self.seller, award_text="Sample Recognition")
        reader = self.render((seller,))
        self.assertIn("Sample Recognition", reader.pages[1].extract_text())
        reader = self.render((self.seller,))
        self.assertNotIn("Sample Recognition", reader.pages[1].extract_text())

    def test_long_order_continues_without_losing_items_or_repeating_total(self):
        items = tuple(SlipItem("Snacks", f"Product number {index:02}", 1, Decimal("1.00")) for index in range(40))
        order = replace(self.order, items=items, total=Decimal("45.25"))
        parts = split_order(order)
        self.assertGreater(len(parts), 1)
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
        text = reader.pages[1].extract_text()
        artwork = reader.pages[1]["/Resources"]["/XObject"]["/FormXob.paid-stamp"].get_object()
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

    def test_empty_report_is_a_valid_empty_pdf(self):
        reader = self.render(())
        self.assertEqual(len(reader.pages), 0)
