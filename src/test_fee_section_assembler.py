import unittest

from src.fee_section_assembler import FeeSectionAssembler
from src.models import LogicalDocumentBlock, PhysicalRow


class TestFeeSectionAssembler(unittest.TestCase):

    @staticmethod
    def make_block(block_id, page, text):
        return LogicalDocumentBlock(
            block_id=block_id,
            type="logical_block",
            page_number=page,
            coordinates={"x1": 0, "y1": 0, "x2": 100, "y2": 100},
            text_content=text,
            physical_rows=[],
            evidence_sources=[],
            fee_candidates=[],
        )

    @staticmethod
    def make_physical_row(page, text, row_index):
        return PhysicalRow(
            page_number=page,
            coordinates={
                "x1": 34.0,
                "y1": row_index * 12.0,
                "x2": 300.0,
                "y2": row_index * 12.0 + 10.0,
            },
            text=text,
            words=[],
            visual_spans=[],
        )
    
    def setUp(self):
        self.assembler = FeeSectionAssembler()

    def test_page_2_current_account_fee_blocks(self):
        blocks = [
            self.make_block("b2", 2, "Current Account"),
            self.make_block(
                "b3",
                2,
                "Opening a current account € 500 "
                "Opening a custody account € 500 "
                "Opening a current account for complex structures1 € 2 000",
            ),
            self.make_block(
                "b4",
                2,
                "Account maintenance Charges € 1 per month/account/mailing address "
                "Account management Charges2 € 625 per quarter/client number "
                "Non-resident current account maintenance € 100 per month/non-resident account "
                "Closing an account € 0",
            ),
            self.make_block(
                "b5",
                2,
                "Debit interest rates for current accounts without arranged overdrafts (per annum)",
            ),
        ]

        sections = self.assembler.assemble(blocks, page_number=2)

        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].heading, "Current Account")
        self.assertEqual(len(sections[0].fee_items), 2)
        self.assertEqual(
            sections[1].heading,
            "Debit interest rates for current accounts without arranged overdrafts (per annum)",
        )

    def test_multiple_fee_items_in_one_block(self):
        rows = [
            self.make_physical_row(
                2,
                "Opening a current account € 500",
                1,
            ),
            self.make_physical_row(
                2,
                "Opening a custody account € 500",
                2,
            ),
            self.make_physical_row(
                2,
                "Opening a current account for complex structures1 € 2 000",
                3,
            ),
        ]

        blocks = [
            LogicalDocumentBlock(
                block_id="b3",
                type="logical_block",
                page_number=2,
                coordinates={"x1": 0, "y1": 0, "x2": 300, "y2": 50},
                text_content=" ".join(row.text for row in rows),
                physical_rows=rows,
                evidence_sources=[],
                fee_candidates=[],
            )
        ]

        sections = self.assembler.assemble(blocks, page_number=2)

        fee_items = [
            item
            for section in sections
            for item in section.fee_items
        ]

        self.assertEqual(len(fee_items), 3)
        self.assertIn(
            "Opening a current account",
            fee_items[0].description,
        )
        self.assertIn(
            "Opening a custody account",
            fee_items[1].description,
        )
        self.assertIn(
            "Opening a current account for complex structures",
            fee_items[2].description,
        )

    def test_fee_item_with_continuation_rows(self):
        rows = [
            self.make_physical_row(
                6,
                "International Credit Transfer % 0.15 from the amount",
                1,
            ),
            self.make_physical_row(
                6,
                "with min. € 5",
                2,
            ),
            self.make_physical_row(
                6,
                "max. € 160",
                3,
            ),
        ]

        blocks = [
            LogicalDocumentBlock(
                block_id="b5",
                type="logical_block",
                page_number=6,
                coordinates={"x1": 0, "y1": 0, "x2": 300, "y2": 50},
                text_content=" ".join(row.text for row in rows),
                physical_rows=rows,
                evidence_sources=[],
                fee_candidates=[],
            )
        ]

        sections = self.assembler.assemble(blocks, page_number=6)

        fee_items = [
            item
            for section in sections
            for item in section.fee_items
        ]

        self.assertEqual(len(fee_items), 1)
        self.assertIn("International Credit Transfer", fee_items[0].description)
        self.assertEqual(fee_items[0].fee_text, "% 0.15")
        self.assertEqual(
            fee_items[0].continuation_text,
            ["with min. € 5", "max. € 160"],
        )

    def test_page_3_inside_business_connect(self):
        blocks = [
            self.make_block(
                "b1",
                3,
                "Account, Transaction and Fee Reporting Electronic reporting",
            ),
            self.make_block(
                "b2",
                3,
                "InsideBusiness Connect (File Transfer, EBICS, Swift)",
            ),
            self.make_block(
                "b3",
                3,
                "End of Day Reporting (MT940, CAMT.053) € 25.00 per month, per account, per format, per channel",
            ),
            self.make_block(
                "b4",
                3,
                "Intraday Reporting (MT942, CAMT.052) € 50.00 per month, per account, per format, per channel",
            ),
        ]

        sections = self.assembler.assemble(blocks, page_number=3)

        self.assertGreaterEqual(len(sections), 1)

        fee_items = [
            item
            for section in sections
            for item in section.fee_items
        ]

        self.assertEqual(len(fee_items), 2)
        self.assertIn("End of Day Reporting", fee_items[0].description)
        self.assertIn("Intraday Reporting", fee_items[1].description)

    def test_footer_is_ignored(self):
        blocks = [
            self.make_block("b1", 3, "Current Account"),
            self.make_block("b2", 3, "Fee € 25 per month"),
            self.make_block(
                "footer",
                3,
                "Tariff brochure LU EN – Wholesale Banking Clients – applicable from 1st June 2026 3",
            ),
        ]

        sections = self.assembler.assemble(blocks, page_number=3)

        all_text = " ".join(
            item.source_text
            for section in sections
            for item in section.fee_items
        )

        self.assertNotIn("Tariff brochure", all_text)

    def test_non_fee_block_does_not_become_fee_item(self):
        blocks = [
            self.make_block("b1", 2, "Current Account"),
            self.make_block(
                "b2",
                2,
                "Debit interest rates for current accounts without arranged overdrafts (per annum)",
            ),
        ]

        sections = self.assembler.assemble(blocks, page_number=2)

        self.assertEqual(len(sections), 2)
        self.assertEqual(len(sections[0].fee_items), 0)
        self.assertEqual(len(sections[1].fee_items), 0)


if __name__ == "__main__":
    unittest.main()