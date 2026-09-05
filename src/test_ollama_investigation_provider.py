import unittest

from src.agent_investigation import (
    AgentConclusion,
    AgentInvestigationRequest,
    AgentInvestigationResult,
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
)
from src.ollama_investigation_provider import (
    MalformedOllamaResultError,
    OllamaInvestigationProvider,
)


class TestOllamaInvestigationProvider(unittest.TestCase):

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
            request_id="ollama-request-1",
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
    def resolved_payload(request_id="ollama-request-1"):
        result = {
            "request_id": request_id,
            "status": "RESOLVED",
            "conclusions": [{
                "conclusion_id": "conclusion-1",
                "subject": "Fee",
                "fields": {"amount": "EUR 25"},
                "evidence_references": [{
                    "source_kind": "physical_row",
                    "source_id": "row-1",
                    "page_number": 6,
                    "row_ids": ["row-1"],
                    "coordinates": {"x1": 10.0, "y1": 0.0, "x2": 200.0, "y2": 10.0},
                }],
                "status": "resolved",
            }],
            "alternatives": [],
            "unresolved_reason": None,
            "missing_or_conflicting_evidence": [],
            "follow_up_requests": [],
            "limitations": [],
        }
        return {"message": {"content": result}}

    def make_provider(self, response=None, transport=None):
        if transport is None:
            transport = lambda url, payload, timeout: response
        return OllamaInvestigationProvider(
            base_url="http://ollama.test/",
            model_name="configured-model:latest",
            timeout_seconds=17.5,
            transport=transport,
        )

    def test_valid_resolved_result(self):
        request = self.make_request()
        provider = self.make_provider(response=self.resolved_payload())

        result = provider.investigate(request)

        self.assertEqual(result.status, "RESOLVED")
        self.assertEqual(result.conclusions[0].evidence_references[0].row_ids, ["row-1"])

    def test_valid_unresolved_result(self):
        request = self.make_request()
        response = {
            "message": {"content": {
                "request_id": request.request_id,
                "status": "UNRESOLVED",
                "conclusions": [],
                "alternatives": [{
                    "hypothesis_id": "h1",
                    "kind": "fee_scope",
                    "summary": "The amount may belong to a neighboring fee.",
                    "source_row_ids": ["row-1"],
                    "source_block_ids": ["block-1"],
                }],
                "unresolved_reason": "The parent fee remains uncertain.",
                "missing_or_conflicting_evidence": [],
                "follow_up_requests": [],
                "limitations": [],
            }}
        }

        result = self.make_provider(response=response).investigate(request)

        self.assertEqual(result.status, "UNRESOLVED")
        self.assertEqual(result.alternatives[0].source_row_ids, ["row-1"])

    def test_valid_insufficient_evidence_result(self):
        request = self.make_request()
        response = {"message": {"content": {
            "request_id": request.request_id,
            "status": "INSUFFICIENT_EVIDENCE",
            "conclusions": [],
            "alternatives": [],
            "unresolved_reason": None,
            "missing_or_conflicting_evidence": ["The page image is unavailable."],
            "follow_up_requests": [],
            "limitations": [],
        }}}

        result = self.make_provider(response=response).investigate(request)

        self.assertEqual(result.status, "INSUFFICIENT_EVIDENCE")

    def test_malformed_model_response(self):
        request = self.make_request()
        response = {"message": {"content": "not-json"}}

        with self.assertRaises(MalformedOllamaResultError):
            self.make_provider(response=response).investigate(request)

    def test_fabricated_provenance_is_rejected(self):
        request = self.make_request()
        response = self.resolved_payload()
        response["message"]["content"]["conclusions"][0]["evidence_references"][0]["source_id"] = "invented-row"
        response["message"]["content"]["conclusions"][0]["evidence_references"][0]["row_ids"] = ["invented-row"]

        with self.assertRaises(InvalidInvestigationResultError):
            self.make_provider(response=response).investigate(request)

    def test_runtime_failure_is_wrapped(self):
        request = self.make_request()

        def failing_transport(url, payload, timeout):
            raise TimeoutError("timed out")

        with self.assertRaises(InvestigationProviderError):
            self.make_provider(transport=failing_transport).investigate(request)

    def test_configuration_is_sent_to_transport(self):
        request = self.make_request()
        calls = []

        def transport(url, payload, timeout):
            calls.append((url, payload, timeout))
            return self.resolved_payload()

        self.make_provider(transport=transport).investigate(request)

        self.assertEqual(calls[0][0], "http://ollama.test/api/chat")
        self.assertEqual(calls[0][1]["model"], "configured-model:latest")
        self.assertFalse(calls[0][1]["stream"])
        self.assertEqual(calls[0][1]["format"], "json")
        self.assertEqual(calls[0][2], 17.5)

    def test_prompt_contains_evidence_and_investigation_rules(self):
        request = self.make_request()
        prompt = OllamaInvestigationProvider.build_prompt(request)

        self.assertIn("RAW EVIDENCE", prompt)
        self.assertIn("Fee EUR 25", prompt)
        self.assertIn("VisualSpans", prompt)
        self.assertIn("deterministic observations", prompt.lower())
        self.assertIn("not a replacement parser", prompt)
        self.assertIn("Do not invent", prompt)
        self.assertIn("evidence_references", prompt)

    def test_provider_implements_provider_protocol(self):
        provider = self.make_provider(response=self.resolved_payload())

        self.assertIsInstance(provider, AgentInvestigationProvider)
        self.assertTrue(callable(provider.investigate))


if __name__ == "__main__":
    unittest.main()
