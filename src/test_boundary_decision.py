#!/usr/bin/env python3
"""Focused tests for the conservative BoundaryDecisionEngine v1."""

import unittest

from src.boundary_decision import BoundaryDecisionEngine
from src.models import BoundaryEvidence


class TestBoundaryDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BoundaryDecisionEngine()

    @staticmethod
    def make_evidence(**overrides):
        values = dict(
            page_number=1,
            row_a_index=0,
            row_b_index=1,
            row_a_text="A",
            row_b_text="B",
            raw_vertical_gap=2.0,
            horizontal_overlap=1.0,
            left_margin_delta=0.0,
            left_margin_similarity=1.0,
            font_size_difference=0.0,
            font_size_similarity=1.0,
            font_family_similarity=1.0,
            bold_relationship="both_regular",
            visual_span_count_a=1,
            visual_span_count_b=1,
            visual_span_composition_a={},
            visual_span_composition_b={},
            page_median_gap=2.0,
            robust_gap_spread=1.0,
            local_gap_ratio=1.0,
            neighborhood_evidence={},
        )
        values.update(overrides)
        return BoundaryEvidence(**values)

    def test_clear_horizontal_discontinuity_returns_split(self):
        evidence = self.make_evidence(
            horizontal_overlap=0.0,
            font_family_similarity=0.0,
            font_size_difference=2.0,
            font_size_similarity=0.8,
            bold_relationship="a_regular_b_bold",
        )

        result = self.engine.decide(evidence)

        self.assertEqual(result.decision, "SPLIT")
        self.assertIn(
            "rows_have_no_horizontal_overlap",
            result.supporting_evidence,
        )

    def test_large_gap_alone_is_ambiguous(self):
        evidence = self.make_evidence(
            raw_vertical_gap=12.75,
            page_median_gap=3.5,
            robust_gap_spread=8.4,
            local_gap_ratio=17.0,
        )

        result = self.engine.decide(evidence)

        self.assertEqual(result.decision, "AMBIGUOUS")

    def test_margin_shift_alone_is_ambiguous(self):
        evidence = self.make_evidence(
            left_margin_delta=237.41,
            left_margin_similarity=0.0,
        )

        result = self.engine.decide(evidence)

        self.assertEqual(result.decision, "AMBIGUOUS")

    def test_typography_change_without_geometry_break_is_ambiguous(self):
        evidence = self.make_evidence(
            font_family_similarity=0.0,
            font_size_difference=2.0,
            font_size_similarity=0.8,
            bold_relationship="a_bold_b_regular",
        )

        result = self.engine.decide(evidence)

        self.assertEqual(result.decision, "AMBIGUOUS")

    def test_matching_visual_evidence_does_not_force_join(self):
        evidence = self.make_evidence(
            horizontal_overlap=1.0,
            left_margin_similarity=1.0,
            font_family_similarity=1.0,
            font_size_similarity=1.0,
            bold_relationship="both_regular",
        )

        result = self.engine.decide(evidence)

        self.assertEqual(result.decision, "AMBIGUOUS")
        self.assertIn(
            "matching_visual_evidence_does_not_prove_structural_continuity",
            result.unresolved_evidence,
        )

    def test_traceability_fields_are_populated(self):
        result = self.engine.decide(self.make_evidence())

        self.assertIsInstance(result.supporting_evidence, list)
        self.assertIsInstance(result.conflicting_evidence, list)
        self.assertIsInstance(result.unresolved_evidence, list)
        self.assertTrue(result.reason)


if __name__ == "__main__":
    unittest.main()