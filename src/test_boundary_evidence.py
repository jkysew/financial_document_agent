#!/usr/bin/env python3
"""
Tests for the evidence-only BoundaryEvidenceProvider.
"""

import os
import sys
import unittest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.boundary_evidence import BoundaryEvidenceProvider
from src.models import PhysicalRow, VisualSpan


def make_span(
    text: str,
    family: str = "TestFont",
    size: float = 9.0,
    flags: int = 0,
) -> VisualSpan:
    return VisualSpan(
        text=text,
        font_family=family,
        font_size=size,
        font_flags=flags,
        color=0,
        bbox={"x0": 0.0, "y0": 0.0, "x1": 10.0, "y1": 10.0},
    )


def make_row(
    page: int,
    text: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    spans=None,
) -> PhysicalRow:
    return PhysicalRow(
        page_number=page,
        coordinates={"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        text=text,
        words=[],
        visual_spans=spans or [],
    )


class TestBoundaryEvidenceProvider(unittest.TestCase):

    def setUp(self):
        self.provider = BoundaryEvidenceProvider()

    def test_basic_boundary_evidence(self):
        rows = [
            make_row(
                1,
                "Row A",
                10,
                100,
                110,
                110,
                [make_span("Row A", size=9.0)],
            ),
            make_row(
                1,
                "Row B",
                10,
                112,
                110,
                122,
                [make_span("Row B", size=9.0)],
            ),
        ]

        evidence = self.provider.get_boundary_evidence(rows, 0)

        self.assertEqual(evidence.page_number, 1)
        self.assertEqual(evidence.row_a_index, 0)
        self.assertEqual(evidence.row_b_index, 1)
        self.assertEqual(evidence.row_a_text, "Row A")
        self.assertEqual(evidence.row_b_text, "Row B")
        self.assertAlmostEqual(evidence.raw_vertical_gap, 2.0)
        self.assertAlmostEqual(evidence.horizontal_overlap, 1.0)
        self.assertEqual(evidence.visual_span_count_a, 1)
        self.assertEqual(evidence.visual_span_count_b, 1)

    def test_no_horizontal_overlap(self):
        rows = [
            make_row(1, "A", 10, 100, 50, 110),
            make_row(1, "B", 60, 112, 100, 122),
        ]

        evidence = self.provider.get_boundary_evidence(rows, 0)

        self.assertEqual(evidence.horizontal_overlap, 0.0)

    def test_partial_horizontal_overlap(self):
        rows = [
            make_row(1, "A", 10, 100, 100, 110),
            make_row(1, "B", 50, 112, 80, 122),
        ]

        evidence = self.provider.get_boundary_evidence(rows, 0)

        # B is 30 pts wide and overlaps A by 30 pts.
        self.assertAlmostEqual(evidence.horizontal_overlap, 1.0)

    def test_font_family_jaccard(self):
        rows = [
            make_row(
                1,
                "A",
                10,
                100,
                100,
                110,
                [
                    make_span("A1", family="FontA"),
                    make_span("A2", family="FontB"),
                ],
            ),
            make_row(
                1,
                "B",
                10,
                112,
                100,
                122,
                [
                    make_span("B1", family="FontA"),
                ],
            ),
        ]

        evidence = self.provider.get_boundary_evidence(rows, 0)

        self.assertAlmostEqual(evidence.font_family_similarity, 0.5)

    def test_bold_detection_uses_pymupdf_bold_flag(self):
        rows = [
            make_row(
                1,
                "Bold",
                10,
                100,
                100,
                110,
                [make_span("Bold", flags=16)],
            ),
            make_row(
                1,
                "Regular",
                10,
                112,
                100,
                122,
                [make_span("Regular", flags=0)],
            ),
        ]

        evidence = self.provider.get_boundary_evidence(rows, 0)

        self.assertEqual(evidence.bold_relationship, "a_bold_b_regular")

    def test_multi_span_composition(self):
        rows = [
            make_row(
                1,
                "A",
                10,
                100,
                100,
                110,
                [
                    make_span("A1", family="FontA", size=9),
                    make_span("A2", family="FontB", size=6, flags=16),
                ],
            ),
            make_row(
                1,
                "B",
                10,
                112,
                100,
                122,
                [make_span("B", family="FontA", size=9)],
            ),
        ]

        evidence = self.provider.get_boundary_evidence(rows, 0)

        composition = evidence.visual_span_composition_a

        self.assertEqual(composition["span_count"], 2)
        self.assertEqual(composition["bold_span_count"], 1)
        self.assertAlmostEqual(composition["bold_span_proportion"], 0.5)
        self.assertEqual(composition["distinct_font_families"], {"FontA", "FontB"})
        self.assertEqual(composition["distinct_font_sizes"], {9, 6})

    def test_local_gap_ratio_excludes_candidate_boundary(self):
        rows = [
            make_row(1, "R1", 10, 0, 100, 10),
            make_row(1, "R2", 10, 12, 100, 22),
            make_row(1, "R3", 10, 24, 100, 34),
            make_row(1, "R4", 10, 44, 100, 54),  # candidate gap = 10
            make_row(1, "R5", 10, 56, 100, 66),
            make_row(1, "R6", 10, 68, 100, 78),
        ]

        evidence = self.provider.get_boundary_evidence(rows, 2)

        # Neighboring gaps excluding candidate are all ~2.
        self.assertGreater(evidence.local_gap_ratio, 4.0)

    def test_invalid_boundary_index(self):
        rows = [
            make_row(1, "A", 10, 0, 100, 10),
        ]

        with self.assertRaises(ValueError):
            self.provider.get_boundary_evidence(rows, 0)


if __name__ == "__main__":
    unittest.main()