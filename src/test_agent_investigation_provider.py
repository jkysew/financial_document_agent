import unittest

from src.agent_investigation import (
    AgentConclusion,
    AgentInvestigationRequest,
    AgentInvestigationResult,
    ContractValidationError,
    EscalationReason,
    EvidenceReference,
    InterpretationHypothesis,
    LogicalBlockEvidence,
    PhysicalRowEvidence,
    VisualSpanEvidence,
)
from src.agent_investigation_provider import (
    AgentInvestigationProvider,
    InvestigationProviderError,
    InvalidInvestigationResultError,
    MockInvestigationProvider,
    execute_investigation,
)


class TestAgentInvestigationProvider(unittest.TestCase):

    @staticmethod
    def make_request():
        row = PhysicalRowEvidence(
            row_id="row-1",
            page_number=6,
            text="Fee EUR 25",
            coordinates={"x1": 10.0, "y1": 0.0, "x2": 200.0, "y2": 10.0},
            visual_spans=[VisualSpanEvidence(
                text="Fee EUR 25",
                font_family="TestFont",
                font_size=9.0,
                font_flags=0,
                color=0,
                bbox={"x0": 10.0, "y0": 0.0, "x1": 200.0, "y1": 10.0},
            )],
        )
        request = AgentInvestigationRequest(
            request_id="request-1",
            document_id="ing-luxembourg",
            trigger_reasons=[EscalationReason(
                code="ambiguous_boundary",
                message="Boundary requires investigation.",
                row_ids=["row-1"],
                block_ids=["block-1"],
            )],
            physical_rows=[row],
            logical_blocks=[LogicalBlockEvidence(
                block_id="block-1",
                page_number=6,
                coordinates={"x1": 10.0, "y1": 0.0, "x2": 200.0, "y2": 10.0},
                text_content="Fee EUR 25",
                row_ids=["row-1"],
            )],
            boundary_assessments=[],
            target_row_ids=["row-1"],
            target_block_ids=["block-1"],
        )
        request.validate()
        return request

    @staticmethod
    def resolved_result(request):
        return AgentInvestigationResult(
            request_id=request.request_id,
            status="RESOLVED",
            conclusions=[AgentConclusion(
                conclusion_id="conclusion-1",
                subject="Fee",
                fields={"amount": "EUR 25"},
                evidence_references=[EvidenceReference(
                    source_kind="physical_row",
                    source_id="row-1",
                    page_number=6,
                    row_ids=["row-1"],
                    coordinates={"x1": 10.0, "y1": 0.0, "x2": 200.0, "y2": 10.0},
                )],
            )],
        )

    def test_mock_provider_returns_valid_default_result(self):
        request = self.make_request()
        provider = MockInvestigationProvider()

        result = execute_investigation(provider, request)

        self.assertIs(result, result)
        self.assertEqual(result.status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(provider.calls, [request])

    def test_resolved_result_with_valid_provenance_passes(self):
        request = self.make_request()
        provider = MockInvestigationProvider(
            result_factory=self.resolved_result,
        )

        result = execute_investigation(provider, request)

        self.assertEqual(result.status, "RESOLVED")
        self.assertEqual(
            result.conclusions[0].evidence_references[0].row_ids,
            ["row-1"],
        )

    def test_fabricated_provenance_is_rejected(self):
        request = self.make_request()

        def fabricated_result(current_request):
            result = self.resolved_result(current_request)
            result.conclusions[0].evidence_references[0].source_id = "invented-row"
            result.conclusions[0].evidence_references[0].row_ids = ["invented-row"]
            return result

        with self.assertRaises(InvalidInvestigationResultError):
            execute_investigation(
                MockInvestigationProvider(result_factory=fabricated_result),
                request,
            )

    def test_unresolved_result_passes_contract_validation(self):
        request = self.make_request()
        provider = MockInvestigationProvider(
            result_factory=lambda current_request: AgentInvestigationResult(
                request_id=current_request.request_id,
                status="UNRESOLVED",
                alternatives=[InterpretationHypothesis(
                    hypothesis_id="alternative-1",
                    kind="fee_scope",
                    summary="The amount may belong to a neighboring fee.",
                    source_row_ids=["row-1"],
                    source_block_ids=["block-1"],
                )],
            )
        )

        result = execute_investigation(provider, request)

        self.assertEqual(result.status, "UNRESOLVED")

    def test_insufficient_evidence_result_passes_contract_validation(self):
        request = self.make_request()
        provider = MockInvestigationProvider(
            result_factory=lambda current_request: AgentInvestigationResult(
                request_id=current_request.request_id,
                status="INSUFFICIENT_EVIDENCE",
                missing_or_conflicting_evidence=[
                    "The relevant page image is unavailable."
                ],
            )
        )

        result = execute_investigation(provider, request)

        self.assertEqual(result.status, "INSUFFICIENT_EVIDENCE")

    def test_provider_failure_is_wrapped(self):
        request = self.make_request()

        class FailingProvider:
            def investigate(self, current_request):
                raise RuntimeError("backend unavailable")

        with self.assertRaises(InvestigationProviderError):
            execute_investigation(FailingProvider(), request)

    def test_provider_protocol_behavior(self):
        provider = MockInvestigationProvider()

        self.assertIsInstance(provider, AgentInvestigationProvider)
        self.assertTrue(callable(provider.investigate))

    def test_invalid_request_is_rejected_before_provider_call(self):
        request = self.make_request()
        request.target_row_ids = ["invented-row"]
        provider = MockInvestigationProvider()

        with self.assertRaises(ContractValidationError):
            execute_investigation(provider, request)

        self.assertEqual(provider.calls, [])


if __name__ == "__main__":
    unittest.main()
