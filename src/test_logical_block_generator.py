import unittest

from src.logical_block_generator import (
    LogicalBlockGenerator,
    compute_row_relationship,
)
from src.models import PhysicalRow, VisualSpan


class TestLogicalBlockGenerator(unittest.TestCase):

    @staticmethod
    def make_row(
        row_index,
        y1,
        y2,
        x1=10.0,
        x2=110.0,
        spans=None,
    ):
        return PhysicalRow(
            page_number=1,
            coordinates={
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
            },
            text=f"Row {row_index}",
            words=[],
            visual_spans=spans or [],
        )

    @staticmethod
    def make_span(family="TestFont", size=9.0, flags=0):
        return VisualSpan(
            text="row",
            font_family=family,
            font_size=size,
            font_flags=flags,
            color=0,
            bbox={"x0": 0.0, "y0": 0.0, "x1": 10.0, "y1": 10.0},
        )

    def setUp(self):
        self.generator = LogicalBlockGenerator()

    def test_explicit_vertical_spacing_threshold_is_preserved(self):
        rows = [
            self.make_row(1, 0.0, 10.0),
            self.make_row(2, 15.0, 25.0),
            self.make_row(3, 115.0, 125.0),
        ]

        blocks = self.generator._group_rows_into_blocks(
            rows,
            vertical_spacing_threshold=10.0,
        )

        self.assertEqual([len(block) for block in blocks], [2, 1])

    def test_zero_vertical_spacing_threshold_preserves_legacy_behavior(self):
        rows = [
            self.make_row(1, 0.0, 10.0),
            self.make_row(2, 10.0, 20.0),
            self.make_row(3, 21.0, 31.0),
        ]

        blocks = self.generator._group_rows_into_blocks(
            rows,
            vertical_spacing_threshold=0,
        )

        self.assertEqual([len(block) for block in blocks], [2, 1])

    def test_negative_vertical_spacing_threshold_preserves_legacy_behavior(self):
        rows = [
            self.make_row(1, 0.0, 10.0),
            self.make_row(2, 9.0, 19.0),
            self.make_row(3, 20.0, 30.0),
        ]

        blocks = self.generator._group_rows_into_blocks(
            rows,
            vertical_spacing_threshold=-1,
        )

        self.assertEqual([len(block) for block in blocks], [2, 1])

    def test_adaptive_grouping_rejects_a_pronounced_gap(self):
        rows = [
            self.make_row(1, 0.0, 10.0),
            self.make_row(2, 15.0, 25.0),
            self.make_row(3, 115.0, 125.0),
        ]

        blocks = self.generator._group_rows_into_blocks(rows)

        self.assertEqual([len(block) for block in blocks], [2, 1])

    def test_adaptive_grouping_keeps_similar_gaps_together(self):
        rows = [
            self.make_row(1, 0.0, 10.0),
            self.make_row(2, 15.0, 25.0),
            self.make_row(3, 30.0, 40.0),
            self.make_row(4, 45.0, 55.0),
        ]

        blocks = self.generator._group_rows_into_blocks(rows)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(len(blocks[0]), 4)

    def test_compute_row_relationship_reports_layout_features(self):
        previous = self.make_row(
            1,
            100.0,
            110.0,
            spans=[
                self.make_span("FontA", 10.0, 32),
                self.make_span("FontB", 10.0),
            ],
        )
        current = self.make_row(
            2,
            115.0,
            125.0,
            x1=20.0,
            x2=80.0,
            spans=[self.make_span("FontB", 8.0)],
        )

        relationship = compute_row_relationship(previous, current)

        self.assertEqual(relationship["vertical_gap"], 5.0)
        self.assertAlmostEqual(relationship["horizontal_overlap"], 1.0)
        self.assertAlmostEqual(relationship["left_margin_similarity"], 0.9)
        self.assertAlmostEqual(relationship["font_size_similarity"], 0.8)
        self.assertAlmostEqual(relationship["font_family_similarity"], 0.5)
        self.assertEqual(relationship["bold_similarity"], 0.0)

    def test_compute_row_relationship_handles_missing_visual_spans(self):
        previous = self.make_row(1, 0.0, 10.0, x1=20.0, x2=20.0)
        current = self.make_row(2, 12.0, 22.0, x1=20.0, x2=20.0)

        relationship = compute_row_relationship(previous, current)

        self.assertEqual(relationship["horizontal_overlap"], 1.0)
        self.assertEqual(relationship["left_margin_similarity"], 1.0)
        self.assertEqual(relationship["font_size_similarity"], 0.5)
        self.assertEqual(relationship["font_family_similarity"], 1.0)
        self.assertEqual(relationship["bold_similarity"], 1.0)


if __name__ == "__main__":
    unittest.main()
