"""Adapter from deterministic gate output to agent investigation requests.

This module only packages existing evidence. It does not interpret documents or
invoke an agent.
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.agent_investigation import (
    AgentInvestigationRequest,
    BoundaryAssessment,
    ContractValidationError,
    EscalationReason,
    InterpretationHypothesis,
    LogicalBlockEvidence,
    PhysicalRowEvidence,
    VisualSpanEvidence,
)
from src.evidence_sufficiency_gate import EvidenceSufficiencyDecision
from src.fee_section_assembler import FeeSection
from src.models import FeeCandidate, LogicalDocumentBlock, PhysicalRow


class AgentInvestigationAdapter:
    """Build a validated investigation request from deterministic evidence."""

    @staticmethod
    def from_gate_decision(
        decision: EvidenceSufficiencyDecision,
        *,
        request_id: str,
        document_id: Optional[str] = None,
        physical_rows: Sequence[PhysicalRow] = (),
        logical_blocks: Sequence[LogicalDocumentBlock] = (),
        boundary_assessments: Sequence[BoundaryAssessment] = (),
        fee_sections: Sequence[FeeSection] = (),
        fee_candidates: Sequence[FeeCandidate] = (),
        hypotheses: Sequence[InterpretationHypothesis] = (),
    ) -> Optional[AgentInvestigationRequest]:
        """Return a request for ESCALATE, or None for CLEAR."""
        if decision.decision == "CLEAR":
            return None
        if decision.decision != "ESCALATE":
            raise ContractValidationError(
                f"Unsupported gate decision: {decision.decision}"
            )

        rows_by_id = {row.row_id: row for row in physical_rows}
        blocks_by_id = {block.block_id: block for block in logical_blocks}
        target_row_ids = AgentInvestigationAdapter._target_ids(
            decision.inspected_row_ids,
            [reason.row_ids for reason in decision.reasons],
        )
        target_block_ids = AgentInvestigationAdapter._target_ids(
            decision.inspected_block_ids,
            [reason.block_ids for reason in decision.reasons],
        )

        AgentInvestigationAdapter._require_known_ids(
            target_row_ids,
            rows_by_id,
            "gate target rows",
        )
        AgentInvestigationAdapter._require_known_ids(
            target_block_ids,
            blocks_by_id,
            "gate target blocks",
        )

        for boundary in boundary_assessments:
            for row_id in (boundary.row_a_id, boundary.row_b_id):
                if row_id is not None:
                    target_row_ids.append(row_id)
            for block_id in boundary.observations.get("block_ids", []):
                target_block_ids.append(block_id)

        for section in fee_sections:
            for item in section.fee_items:
                target_block_ids.extend(item.source_blocks)

        target_row_ids = AgentInvestigationAdapter._unique(target_row_ids)
        target_block_ids = AgentInvestigationAdapter._unique(target_block_ids)
        AgentInvestigationAdapter._require_known_ids(
            target_row_ids,
            rows_by_id,
            "boundary or fee target rows",
        )
        AgentInvestigationAdapter._require_known_ids(
            target_block_ids,
            blocks_by_id,
            "boundary or fee target blocks",
        )

        selected_rows = [
            row
            for row in physical_rows
            if row.row_id in set(target_row_ids)
            or row.row_id in {
                block_row.row_id
                for block in logical_blocks
                if block.block_id in target_block_ids
                for block_row in block.physical_rows
            }
        ]
        selected_blocks = [
            block for block in logical_blocks if block.block_id in set(target_block_ids)
        ]

        request = AgentInvestigationRequest(
            request_id=request_id,
            document_id=document_id,
            trigger_reasons=[
                EscalationReason(
                    code=reason.code,
                    message=reason.message,
                    row_ids=list(reason.row_ids),
                    block_ids=list(reason.block_ids),
                    evidence=dict(reason.evidence),
                )
                for reason in decision.reasons
            ],
            physical_rows=[
                AgentInvestigationAdapter._row_evidence(row)
                for row in selected_rows
            ],
            logical_blocks=[
                AgentInvestigationAdapter._block_evidence(block)
                for block in selected_blocks
            ],
            boundary_assessments=list(boundary_assessments),
            target_row_ids=target_row_ids,
            target_block_ids=target_block_ids,
            fee_items=(
                AgentInvestigationAdapter._fee_items(fee_sections, selected_blocks)
                + AgentInvestigationAdapter._fee_candidates(
                    list(fee_candidates)
                    + [
                        candidate
                        for block in selected_blocks
                        for candidate in block.fee_candidates
                        if candidate.candidate_id not in {
                            item.candidate_id for item in fee_candidates
                        }
                    ]
                )
            ),
            hypotheses=list(hypotheses),
        )
        request.validate()
        return request

    @staticmethod
    def _target_ids(
        inspected_ids: Iterable[str],
        reason_id_lists: Iterable[Iterable[str]],
    ) -> List[str]:
        values = list(inspected_ids)
        for ids in reason_id_lists:
            values.extend(ids)
        return AgentInvestigationAdapter._unique(values)

    @staticmethod
    def _unique(values: Iterable[str]) -> List[str]:
        return list(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _require_known_ids(
        ids: Iterable[str],
        known: Dict[str, Any],
        label: str,
    ) -> None:
        unknown = set(ids) - set(known)
        if unknown:
            raise ContractValidationError(
                f"Unknown {label}: {sorted(unknown)}"
            )

    @staticmethod
    def _row_evidence(row: PhysicalRow) -> PhysicalRowEvidence:
        return PhysicalRowEvidence(
            row_id=row.row_id,
            page_number=row.page_number,
            text=row.text,
            coordinates=dict(row.coordinates),
            words=list(row.words),
            visual_spans=[
                VisualSpanEvidence(
                    text=span.text,
                    font_family=span.font_family,
                    font_size=span.font_size,
                    font_flags=span.font_flags,
                    color=span.color,
                    bbox=dict(span.bbox),
                )
                for span in row.visual_spans
            ],
        )

    @staticmethod
    def _block_evidence(block: LogicalDocumentBlock) -> LogicalBlockEvidence:
        return LogicalBlockEvidence(
            block_id=block.block_id,
            page_number=block.page_number,
            coordinates=dict(block.coordinates),
            text_content=block.text_content,
            row_ids=[row.row_id for row in block.physical_rows],
            fee_candidate_ids=[
                candidate.candidate_id
                for candidate in block.fee_candidates
            ],
            status=block.status.value,
            confidence_score=block.confidence_score,
        )

    @staticmethod
    def _fee_items(
        fee_sections: Sequence[FeeSection],
        selected_blocks: Sequence[LogicalDocumentBlock],
    ) -> List[Dict[str, Any]]:
        selected_block_ids = {block.block_id for block in selected_blocks}
        items: List[Dict[str, Any]] = []
        for section_index, section in enumerate(fee_sections):
            for item_index, item in enumerate(section.fee_items):
                source_blocks = [
                    block_id
                    for block_id in item.source_blocks
                    if block_id in selected_block_ids
                ]
                if not source_blocks:
                    continue
                items.append({
                    "fee_item_id": f"fee_item:{section_index}:{item_index}",
                    "description": item.description,
                    "source_block_ids": source_blocks,
                    "source_text": item.source_text,
                    "fee_text": item.fee_text,
                    "occurrence_text": item.occurrence_text,
                    "continuation_text": list(item.continuation_text),
                    "tiers": list(item.tiers),
                })
        return items

    @staticmethod
    def _fee_candidates(
        fee_candidates: Sequence[FeeCandidate],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "kind": "fee_candidate",
                "fee_candidate_id": candidate.candidate_id,
                "description": candidate.description,
                "amount": candidate.amount,
                "currency": candidate.currency,
                "unit": candidate.unit,
                "pricing_type": candidate.pricing_type,
                "source_page": candidate.source_page,
                "source_coordinates": candidate.source_coordinates,
                "evidence_text": candidate.evidence_text,
                "status": candidate.status.value,
            }
            for candidate in fee_candidates
        ]
