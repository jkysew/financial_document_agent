import unittest

from src.agent_investigation import (
    AgentConclusion,
    AgentInvestigationRequest,
    AgentInvestigationResult,
    BoundaryAssessment,
    ContractValidationError,
    EscalationReason,
    EvidenceReference,
    EvidenceRequest,
    InterpretationHypothesis,
    LogicalBlockEvidence,
    PhysicalRowEvidence,
    VisualSpanEvidence,
)


class TestAgentInvestigationContract(unittest.TestCase):

    @staticmethod
    def make_row(row_id="row-1", text="Fee EUR 25"):
        return PhysicalRowEvidence(
            row_id=row_id,
            page_number=6,
            text=text,
            coordinates={"x1": 34.0, "y1": 100.0, "x2": 300.0, "y2": 110.0},
            words=[{"text": text, "x": 34.0, "y": 100.0}],
            visual_spans=[
                VisualSpanEvidence(
                    text=text,
                    font_family="TestFont",
                    font_size=9.0,
                    font_flags=0,
                    color=0,
                    bbox={"x0": 34.0, "y0": 100.0, "x1": 300.0, "y1": 110.0},
                )
            ],
        )

    def make_request(self):
        rows = [
            self.make_row("row-1", "International Credit Transfer % 0.15"),
            self.make_row("row-2", "with min. EUR 5"),
            self.make_row("row-3", "max. EUR 160"),
        ]
        return AgentInvestigationRequest(
            request_id="investigation-1",
            document_id="ing-luxembourg",
            trigger_reasons=[
                EscalationReason(
                    code="ambiguous_boundary",
                    message="Parent fee association is ambiguous.",
                    row_ids=["row-1", "row-2"],
                    block_ids=["block-1"],
                    evidence={"page_number": 6},
                )
            ],
            physical_rows=rows,
            logical_blocks=[
                LogicalBlockEvidence(
                    block_id="block-1",
                    page_number=6,
                    coordinates={"x1": 34.0, "y1": 100.0, "x2": 300.0, "y2": 130.0},
                    text_content="International Credit Transfer % 0.15 with min. EUR 5 max. EUR 160",
                    row_ids=["row-1", "row-2", "row-3"],
                )
            ],
            boundary_assessments=[
                BoundaryAssessment(
                    page_number=6,
                    row_a_index=0,
                    row_b_index=1,
                    row_a_id="row-1",
                    row_b_id="row-2",
                    row_a_text="International Credit Transfer % 0.15",
                    row_b_text="with min. EUR 5",
                    row_a_coordinates=rows[0].coordinates,
                    row_b_coordinates=rows[1].coordinates,
                    decision="AMBIGUOUS",
                    decision_reason="The boundary does not prove parentage.",
                    unresolved_evidence=["visual continuity is not semantic proof"],
                    observations={"vertical_gap": 2.0},
                )
            ],
            fee_items=[
                {
                    "description": "International Credit Transfer",
                    "source_block_ids": ["block-1"],
                    "source_row_ids": ["row-1", "row-2", "row-3"],
                    "fee_text": "% 0.15",
                }
            ],
            hypotheses=[
                InterpretationHypothesis(
                    hypothesis_id="h-continuation",
                    kind="parent_continuation",
                    summary="Minimum and maximum rows belong to the transfer fee.",
                    source_row_ids=["row-1", "row-2", "row-3"],
                    source_block_ids=["block-1"],
                )
            ],
        )

    def test_request_serialization_round_trip_preserves_provenance(self):
        request = self.make_request()

        serialized = request.to_dict()
        restored = AgentInvestigationRequest.from_dict(serialized)

        self.assertEqual(restored.request_id, "investigation-1")
        self.assertEqual(restored.physical_rows[0].row_id, "row-1")
        self.assertEqual(restored.physical_rows[0].page_number, 6)
        self.assertEqual(restored.physical_rows[0].coordinates["x1"], 34.0)
        self.assertEqual(
            restored.physical_rows[0].visual_spans[0].font_family,
            "TestFont",
        )
        self.assertEqual(restored.logical_blocks[0].row_ids, ["row-1", "row-2", "row-3"])
        self.assertEqual(restored.boundary_assessments[0].row_a_id, "row-1")
        self.assertEqual(restored.hypotheses[0].source_block_ids, ["block-1"])

    def test_result_serialization_round_trip(self):
        result = AgentInvestigationResult(
            request_id="investigation-1",
            status="RESOLVED",
            conclusions=[
                AgentConclusion(
                    conclusion_id="c1",
                    subject="International Credit Transfer",
                    fields={"minimum": "EUR 5", "maximum": "EUR 160"},
                    evidence_references=[
                        EvidenceReference(
                            source_kind="physical_row",
                            source_id="row-2",
                            page_number=6,
                            row_ids=["row-2"],
                            coordinates={"x1": 34.0, "y1": 100.0, "x2": 300.0, "y2": 110.0},
                        )
                    ],
                )
            ],
        )

        restored = AgentInvestigationResult.from_dict(result.to_dict())

        self.assertEqual(restored.status, "RESOLVED")
        self.assertEqual(
            restored.conclusions[0].evidence_references[0].row_ids,
            ["row-2"],
        )

        restored.validate_against(self.make_request())

    def test_invented_row_id_fails_request_aware_validation(self):
        result = AgentInvestigationResult(
            request_id="investigation-1",
            status="RESOLVED",
            conclusions=[
                AgentConclusion(
                    conclusion_id="c1",
                    subject="fee",
                    fields={"amount": "EUR 25"},
                    evidence_references=[EvidenceReference(
                        source_kind="physical_row",
                        source_id="invented-row",
                        page_number=6,
                    )],
                )
            ],
        )

        with self.assertRaises(ContractValidationError):
            result.validate_against(self.make_request())

    def test_invented_block_id_fails_request_aware_validation(self):
        result = AgentInvestigationResult(
            request_id="investigation-1",
            status="RESOLVED",
            conclusions=[
                AgentConclusion(
                    conclusion_id="c1",
                    subject="fee",
                    fields={"amount": "EUR 25"},
                    evidence_references=[EvidenceReference(
                        source_kind="logical_block",
                        source_id="invented-block",
                        block_ids=["invented-block"],
                    )],
                )
            ],
        )

        with self.assertRaises(ContractValidationError):
            result.validate_against(self.make_request())

    def test_invalid_boundary_reference_fails_request_aware_validation(self):
        result = AgentInvestigationResult(
            request_id="investigation-1",
            status="RESOLVED",
            conclusions=[
                AgentConclusion(
                    conclusion_id="c1",
                    subject="fee association",
                    fields={"parent": "transfer"},
                    evidence_references=[EvidenceReference(
                        source_kind="boundary_assessment",
                        source_id="6:9:10",
                        page_number=6,
                        row_ids=["row-1", "row-2"],
                    )],
                )
            ],
        )

        with self.assertRaises(ContractValidationError):
            result.validate_against(self.make_request())

    def test_mismatched_page_or_source_identity_fails(self):
        result = AgentInvestigationResult(
            request_id="investigation-1",
            status="RESOLVED",
            conclusions=[
                AgentConclusion(
                    conclusion_id="c1",
                    subject="fee",
                    fields={"amount": "EUR 25"},
                    evidence_references=[EvidenceReference(
                        source_kind="physical_row",
                        source_id="row-1",
                        page_number=7,
                        row_ids=["row-1"],
                    )],
                )
            ],
        )

        with self.assertRaises(ContractValidationError):
            result.validate_against(self.make_request())

    def test_invalid_source_kind_fails_structural_validation(self):
        reference = EvidenceReference(
            source_kind="invented_source",
            source_id="row-1",
            page_number=6,
        )

        with self.assertRaises(ContractValidationError):
            reference.validate()

    def test_resolved_requires_conclusion_with_provenance(self):
        with self.assertRaises(ContractValidationError):
            AgentInvestigationResult(
                request_id="r1",
                status="RESOLVED",
                conclusions=[],
            ).validate()

        conclusion = AgentConclusion(
            conclusion_id="c1",
            subject="fee",
            fields={"amount": "EUR 25"},
        )
        with self.assertRaises(ContractValidationError):
            conclusion.validate()

    def test_resolved_conclusion_rejects_empty_evidence_reference(self):
        conclusion = AgentConclusion(
            conclusion_id="c1",
            subject="fee",
            fields={"amount": "EUR 25"},
            evidence_references=[EvidenceReference(source_kind="physical_row")],
        )

        with self.assertRaises(ContractValidationError):
            conclusion.validate()

    def test_unresolved_result_requires_alternative_or_reason(self):
        valid = AgentInvestigationResult(
            request_id="r1",
            status="UNRESOLVED",
            alternatives=[
                InterpretationHypothesis(
                    hypothesis_id="h1",
                    kind="footnote_scope",
                    summary="Footnote may constrain the tier or the whole fee.",
                )
            ],
        )
        valid.validate()

        with self.assertRaises(ContractValidationError):
            AgentInvestigationResult(
                request_id="r1",
                status="UNRESOLVED",
            ).validate()

    def test_insufficient_evidence_requires_explanation(self):
        valid = AgentInvestigationResult(
            request_id="r1",
            status="INSUFFICIENT_EVIDENCE",
            missing_or_conflicting_evidence=[
                "The tier table continues on an unavailable page."
            ],
        )
        valid.validate()

        with self.assertRaises(ContractValidationError):
            AgentInvestigationResult(
                request_id="r1",
                status="INSUFFICIENT_EVIDENCE",
            ).validate()

    def test_evidence_requests_are_observational_and_bounded(self):
        valid_requests = [
            EvidenceRequest(
                request_id="e1",
                request_type="page_region",
                purpose="Inspect the footnote marker and amount.",
                page_number=6,
                coordinates={"x1": 30.0, "y1": 200.0, "x2": 310.0, "y2": 260.0},
                max_results=1,
            ),
            EvidenceRequest(
                request_id="e2",
                request_type="neighboring_rows",
                purpose="Inspect rows around the ambiguous parent.",
                row_ids=["row-1"],
            ),
            EvidenceRequest(
                request_id="e3",
                request_type="text_search",
                purpose="Find repeated fee terminology.",
                query="International Credit Transfer",
            ),
        ]
        for request in valid_requests:
            request.validate()

        with self.assertRaises(ContractValidationError):
            EvidenceRequest(
                request_id="e4",
                request_type="interpret_fee",
                purpose="Choose the fee.",
            ).validate()

        with self.assertRaises(ContractValidationError):
            EvidenceRequest(
                request_id="e5",
                request_type="page_image",
                purpose="Inspect page.",
                page_number=6,
                max_results=101,
            ).validate()

    def test_page6_competing_tier_and_footnote_hypotheses_preserve_sources(self):
        request = self.make_request()
        request.physical_rows.append(
            self.make_row("row-4", ">100 0006 EUR 100")
        )
        request.hypotheses.extend([
            InterpretationHypothesis(
                hypothesis_id="h-tier-footnote",
                kind="footnote_scope",
                summary="The trailing 6 is a footnote marker for EUR 100.",
                source_row_ids=["row-4"],
                source_block_ids=["block-1"],
            ),
            InterpretationHypothesis(
                hypothesis_id="h-tier-split",
                kind="tier_association",
                summary="The final tier continues in another block or page.",
                source_row_ids=["row-4"],
                source_block_ids=["block-1"],
            ),
        ])

        request.validate()

        self.assertEqual(
            {hypothesis.kind for hypothesis in request.hypotheses},
            {"parent_continuation", "footnote_scope", "tier_association"},
        )
        self.assertEqual(request.hypotheses[-1].source_row_ids, ["row-4"])


if __name__ == "__main__":
    unittest.main()
