import unittest

from src.boundary_decision import BoundaryDecision
from src.evidence_sufficiency_gate import EvidenceSufficiencyGate
from src.fee_section_assembler import FeeItem, FeeSection
from src.models import (
    BoundaryEvidence,
    LogicalDocumentBlock,
    PhysicalRow,
    VisualSpan,
)


class TestEvidenceSufficiencyGate(unittest.TestCase):

    @staticmethod
    def make_row(row_id, text, y1=0.0, y2=10.0):
        return PhysicalRow(
            page_number=6,
            coordinates={"x1": 10.0, "y1": y1, "x2": 200.0, "y2": y2},
            text=text,
            words=[],
            visual_spans=[
                VisualSpan(
                    text=text,
                    font_family="TestFont",
                    font_size=9.0,
                    font_flags=0,
                    color=0,
                    bbox={"x0": 10.0, "y0": y1, "x1": 200.0, "y1": y2},
                )
            ],
            row_id=row_id,
        )

    @staticmethod
    def make_block(block_id, rows):
        return LogicalDocumentBlock(
            block_id=block_id,
            type="logical_block",
            page_number=6,
            coordinates={"x1": 10.0, "y1": 0.0, "x2": 200.0, "y2": 100.0},
            text_content=" ".join(row.text for row in rows),
            physical_rows=rows,
            evidence_sources=[],
            fee_candidates=[],
        )

    @staticmethod
    def make_boundary_evidence(row_a_text, row_b_text, overlap=1.0):
        return BoundaryEvidence(
            page_number=6,
            row_a_index=0,
            row_b_index=1,
            row_a_text=row_a_text,
            row_b_text=row_b_text,
            raw_vertical_gap=2.0,
            horizontal_overlap=overlap,
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
            robust_gap_spread=0.0,
            local_gap_ratio=1.0,
            neighborhood_evidence={},
        )

    def setUp(self):
        self.gate = EvidenceSufficiencyGate()

    def test_clear_for_supported_fee_with_resolved_continuation(self):
        rows = [
            self.make_row("r1", "Single Credit Transfer € 25"),
            self.make_row("r2", "with min. € 5", 12.0, 22.0),
        ]
        block = self.make_block("b1", rows)
        section = FeeSection(
            heading=None,
            source_blocks=["b1"],
            fee_items=[
                FeeItem(
                    description="Single Credit Transfer",
                    source_blocks=["b1"],
                    source_text="Single Credit Transfer € 25 with min. € 5",
                    fee_text="€ 25",
                    continuation_text=["with min. € 5"],
                )
            ],
        )

        decision = self.gate.evaluate([block], [section])

        self.assertEqual(decision.decision, "CLEAR")
        self.assertEqual(decision.inspected_block_ids, ["b1"])
        self.assertEqual(decision.inspected_row_ids, ["r1", "r2"])

    def test_table_is_clear_when_tiers_are_resolved(self):
        rows = [
            self.make_row("r1", "Transfer labelled OUR"),
            self.make_row("r2", "Amount of transfer in euro"),
            self.make_row("r3", "≤12 500 € 8"),
            self.make_row("r4", ">12 500 € 25"),
            self.make_row("r5", ">25 000 € 40"),
        ]
        block = self.make_block("b1", rows)
        section = FeeSection(
            heading=None,
            source_blocks=["b1"],
            fee_items=[
                FeeItem(
                    description="Transfer labelled OUR",
                    source_blocks=["b1"],
                    source_text=" ".join(row.text for row in rows),
                    tiers=[
                        {"threshold": "≤12 500", "fee": "€ 8"},
                        {"threshold": ">12 500", "fee": "€ 25"},
                        {"threshold": ">25 000", "fee": "€ 40"},
                    ],
                )
            ],
        )

        decision = self.gate.evaluate([block], [section])

        self.assertEqual(decision.decision, "CLEAR")

    def test_ambiguous_boundary_escalates_with_reason(self):
        rows = [
            self.make_row("r1", "Fee € 25"),
            self.make_row("r2", "with min. € 5", 12.0, 22.0),
        ]
        block = self.make_block("b1", rows)
        section = FeeSection(
            heading=None,
            source_blocks=["b1"],
            fee_items=[FeeItem(
                description="Fee",
                source_blocks=["b1"],
                source_text="Fee € 25",
                fee_text="€ 25",
            )],
        )
        boundary = BoundaryDecision(
            decision="AMBIGUOUS",
            supporting_evidence=[],
            conflicting_evidence=[],
            unresolved_evidence=["uncertain boundary"],
            reason="Insufficient evidence",
        )

        evidence = self.make_boundary_evidence(rows[0].text, rows[1].text)
        decision = self.gate.evaluate(
            [block],
            [section],
            [boundary],
            [evidence],
        )

        self.assertEqual(decision.decision, "ESCALATE")
        self.assertEqual(decision.reasons[0].code, "ambiguous_boundary")
        reason = decision.reasons[0]
        self.assertEqual(reason.block_ids, ["b1"])
        self.assertEqual(reason.row_ids, ["r1", "r2"])
        self.assertEqual(reason.evidence["page_number"], 6)
        self.assertEqual(reason.evidence["row_a_index"], 0)
        self.assertEqual(reason.evidence["row_b_index"], 1)
        self.assertEqual(reason.evidence["row_a_text"], rows[0].text)
        self.assertEqual(reason.evidence["row_b_text"], rows[1].text)
        self.assertEqual(
            reason.evidence["row_a_coordinates"],
            rows[0].coordinates,
        )
        self.assertEqual(
            reason.evidence["row_b_coordinates"],
            rows[1].coordinates,
        )

    def test_conflicting_boundary_evidence_escalates(self):
        rows = [
            self.make_row("r1", "Fee € 25"),
            self.make_row("r2", "with min. € 5", 12.0, 22.0),
        ]
        block = self.make_block("b1", rows)
        boundary = BoundaryDecision(
            decision="SPLIT",
            supporting_evidence=["separate regions"],
            conflicting_evidence=["same fee row pattern"],
            unresolved_evidence=[],
            reason="Conflicting structural signals",
        )

        evidence = self.make_boundary_evidence(
            rows[0].text,
            rows[1].text,
            overlap=1.5,
        )
        decision = self.gate.evaluate(
            [block],
            [],
            [boundary],
            [evidence],
        )

        self.assertEqual(decision.decision, "ESCALATE")
        self.assertIn(
            "conflicting_structural_evidence",
            {reason.code for reason in decision.reasons},
        )
        conflict = next(
            reason
            for reason in decision.reasons
            if reason.code == "conflicting_structural_evidence"
        )
        self.assertEqual(conflict.row_ids, ["r1", "r2"])
        self.assertEqual(conflict.evidence["page_number"], 6)
        self.assertEqual(conflict.evidence["row_a_text"], rows[0].text)
        self.assertEqual(conflict.evidence["row_b_text"], rows[1].text)

        measurement_conflict = next(
            reason
            for reason in decision.reasons
            if reason.code == "contradictory_physical_visual_evidence"
        )
        self.assertEqual(measurement_conflict.row_ids, ["r1", "r2"])

    def test_missing_boundary_decisions_do_not_invent_provenance(self):
        row = self.make_row("r1", "Fee € 25")
        block = self.make_block("b1", [row])

        decision = self.gate.evaluate([block], [])

        self.assertEqual(decision.decision, "CLEAR")
        self.assertEqual(decision.reasons, [])

    def test_missing_visual_evidence_escalates(self):
        row = PhysicalRow(
            page_number=6,
            coordinates={"x1": 10.0, "y1": 0.0, "x2": 200.0, "y2": 10.0},
            text="Fee € 25",
            words=[],
            visual_spans=[],
            row_id="r1",
        )
        block = self.make_block("b1", [row])
        section = FeeSection(
            heading=None,
            source_blocks=["b1"],
            fee_items=[FeeItem(
                description="Fee",
                source_blocks=["b1"],
                source_text="Fee € 25",
                fee_text="€ 25",
            )],
        )

        decision = self.gate.evaluate([block], [section])

        self.assertEqual(decision.decision, "ESCALATE")
        self.assertIn(
            "missing_visual_evidence",
            {reason.code for reason in decision.reasons},
        )

    def test_unresolved_associations_and_references_escalate(self):
        rows = [
            self.make_row("r1", "International Credit Transfer € 25"),
            self.make_row("r2", "with min. € 5", 12.0, 22.0),
            self.make_row("r3", "6 Maximum EUR 25 000", 24.0, 34.0),
        ]
        block = self.make_block("b1", rows)
        block.text_content += " Cf standard pricing"
        section = FeeSection(
            heading=None,
            source_blocks=["b1"],
            fee_items=[FeeItem(
                description="International Credit Transfer",
                source_blocks=["b1"],
                source_text="International Credit Transfer € 25",
                fee_text="€ 25",
            )],
        )

        decision = self.gate.evaluate([block], [section])
        codes = {reason.code for reason in decision.reasons}

        self.assertEqual(decision.decision, "ESCALATE")
        self.assertIn("unresolved_parent_continuation", codes)
        self.assertIn("unresolved_footnote_association", codes)
        self.assertIn("unresolved_cross_reference", codes)

    def test_unsupported_fee_value_escalates(self):
        row = self.make_row("r1", "Variable service fee")
        block = self.make_block("b1", [row])
        section = FeeSection(
            heading=None,
            source_blocks=["b1"],
            fee_items=[FeeItem(
                description="Variable service fee",
                source_blocks=["b1"],
                source_text="Variable service fee",
            )],
        )

        decision = self.gate.evaluate([block], [section])

        self.assertEqual(decision.decision, "ESCALATE")
        self.assertIn(
            "unsupported_required_fee_field",
            {reason.code for reason in decision.reasons},
        )


if __name__ == "__main__":
    unittest.main()
