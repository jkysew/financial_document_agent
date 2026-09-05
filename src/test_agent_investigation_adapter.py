import unittest

from src.agent_investigation import (
    BoundaryAssessment,
    ContractValidationError,
    InterpretationHypothesis,
)
from src.agent_investigation_adapter import AgentInvestigationAdapter
from src.evidence_sufficiency_gate import (
    EvidenceSufficiencyDecision,
    GateReason,
)
from src.fee_section_assembler import FeeItem, FeeSection
from src.models import LogicalDocumentBlock, PhysicalRow, VisualSpan


class TestAgentInvestigationAdapter(unittest.TestCase):

    @staticmethod
    def make_row(row_id, text, y1=0.0, y2=10.0):
        return PhysicalRow(
            page_number=6,
            coordinates={"x1": 34.0, "y1": y1, "x2": 300.0, "y2": y2},
            text=text,
            words=[],
            visual_spans=[
                VisualSpan(
                    text=text,
                    font_family="TestFont",
                    font_size=9.0,
                    font_flags=0,
                    color=0,
                    bbox={"x0": 34.0, "y0": y1, "x1": 300.0, "y1": y2},
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
            coordinates={"x1": 34.0, "y1": 0.0, "x2": 300.0, "y2": 100.0},
            text_content=" ".join(row.text for row in rows),
            physical_rows=rows,
            evidence_sources=[],
            fee_candidates=[],
        )

    @staticmethod
    def escalate(row_ids, block_ids):
        return EvidenceSufficiencyDecision(
            decision="ESCALATE",
            reasons=[GateReason(
                code="ambiguous_boundary",
                message="Deterministic parentage is unresolved.",
                row_ids=list(row_ids),
                block_ids=list(block_ids),
                evidence={"page_number": 6},
            )],
            inspected_row_ids=list(row_ids),
            inspected_block_ids=list(block_ids),
        )

    def test_clear_produces_no_request(self):
        decision = EvidenceSufficiencyDecision(decision="CLEAR")

        request = AgentInvestigationAdapter.from_gate_decision(
            decision,
            request_id="clear-1",
        )

        self.assertIsNone(request)

    def test_escalate_produces_valid_request_with_provenance(self):
        rows = [self.make_row("r1", "Fee EUR 25")]
        block = self.make_block("b1", rows)
        decision = self.escalate(["r1"], ["b1"])

        request = AgentInvestigationAdapter.from_gate_decision(
            decision,
            request_id="investigation-1",
            document_id="ing-luxembourg",
            physical_rows=rows,
            logical_blocks=[block],
        )

        self.assertIsNotNone(request)
        request.validate()
        self.assertEqual(request.document_id, "ing-luxembourg")
        self.assertEqual(request.target_row_ids, ["r1"])
        self.assertEqual(request.target_block_ids, ["b1"])
        self.assertEqual(request.physical_rows[0].row_id, "r1")
        self.assertEqual(request.physical_rows[0].page_number, 6)
        self.assertEqual(request.physical_rows[0].visual_spans[0].font_family, "TestFont")
        self.assertEqual(request.logical_blocks[0].block_id, "b1")

    def test_page6_continuation_ambiguity_preserves_rows_and_fee_item(self):
        rows = [
            self.make_row("r1", "International Credit Transfer % 0.15"),
            self.make_row("r2", "with min. EUR 5", 12.0, 22.0),
            self.make_row("r3", "max. EUR 160", 24.0, 34.0),
        ]
        block = self.make_block("b1", rows)
        section = FeeSection(
            heading=None,
            source_blocks=["b1"],
            fee_items=[FeeItem(
                description="International Credit Transfer",
                source_blocks=["b1"],
                source_text=" ".join(row.text for row in rows),
                fee_text="% 0.15",
                continuation_text=["with min. EUR 5", "max. EUR 160"],
            )],
        )

        request = AgentInvestigationAdapter.from_gate_decision(
            self.escalate(["r1", "r2", "r3"], ["b1"]),
            request_id="continuation-1",
            physical_rows=rows,
            logical_blocks=[block],
            fee_sections=[section],
            hypotheses=[InterpretationHypothesis(
                hypothesis_id="h1",
                kind="parent_continuation",
                summary="The min/max rows belong to the transfer fee.",
                source_row_ids=["r1", "r2", "r3"],
                source_block_ids=["b1"],
            )],
        )

        self.assertEqual(len(request.fee_items), 1)
        self.assertEqual(request.fee_items[0]["continuation_text"], [
            "with min. EUR 5",
            "max. EUR 160",
        ])
        self.assertEqual(request.hypotheses[0].source_row_ids, ["r1", "r2", "r3"])

    def test_page6_tier_and_footnote_evidence_are_kept_raw(self):
        rows = [
            self.make_row("r1", "Transfer labelled OUR"),
            self.make_row("r2", "Amount of transfer in euro", 12.0, 22.0),
            self.make_row("r3", ">100 0006 EUR 100", 24.0, 34.0),
            self.make_row("r4", "6 Maximum EUR 25 000", 100.0, 110.0),
        ]
        block = self.make_block("b1", rows)
        request = AgentInvestigationAdapter.from_gate_decision(
            self.escalate([row.row_id for row in rows], ["b1"]),
            request_id="tier-footnote-1",
            physical_rows=rows,
            logical_blocks=[block],
            hypotheses=[
                InterpretationHypothesis(
                    hypothesis_id="h-footnote",
                    kind="footnote_scope",
                    summary="The 6 is a footnote marker for the final tier.",
                    source_row_ids=["r3", "r4"],
                    source_block_ids=["b1"],
                )
            ],
        )

        self.assertEqual(request.physical_rows[2].text, ">100 0006 EUR 100")
        self.assertEqual(request.physical_rows[3].text, "6 Maximum EUR 25 000")
        self.assertEqual(request.hypotheses[0].kind, "footnote_scope")

    def test_missing_optional_evidence_is_safe(self):
        decision = EvidenceSufficiencyDecision(
            decision="ESCALATE",
            reasons=[GateReason(
                code="missing_visual_evidence",
                message="Visual evidence is unavailable.",
            )],
        )

        request = AgentInvestigationAdapter.from_gate_decision(
            decision,
            request_id="missing-evidence-1",
        )

        self.assertIsNotNone(request)
        self.assertEqual(request.physical_rows, [])
        self.assertEqual(request.logical_blocks, [])
        self.assertEqual(request.boundary_assessments, [])
        request.validate()

    def test_fabricated_or_mismatched_references_are_rejected(self):
        rows = [self.make_row("r1", "Fee EUR 25")]
        block = self.make_block("b1", rows)
        decision = self.escalate(["invented-row"], ["b1"])

        with self.assertRaises(ValueError):
            AgentInvestigationAdapter.from_gate_decision(
                decision,
                request_id="bad-row-1",
                physical_rows=rows,
                logical_blocks=[block],
            )

        boundary = BoundaryAssessment(
            page_number=6,
            row_a_index=0,
            row_b_index=1,
            row_a_id="r1",
            row_b_id="invented-row",
            row_a_text="Fee EUR 25",
            row_b_text="missing",
            row_a_coordinates=rows[0].coordinates,
            row_b_coordinates=None,
            decision="AMBIGUOUS",
            decision_reason="Missing row",
        )
        with self.assertRaises(ContractValidationError):
            AgentInvestigationAdapter.from_gate_decision(
                self.escalate(["r1"], ["b1"]),
                request_id="bad-boundary-1",
                physical_rows=rows,
                logical_blocks=[block],
                boundary_assessments=[boundary],
            )


if __name__ == "__main__":
    unittest.main()
