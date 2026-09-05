"""Evidence sufficiency gate for deterministic document analysis.

The gate does not interpret documents or invoke an agent. It records whether
current deterministic evidence is sufficient for acceptance or should be sent
to a future investigation/agent stage.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence
import re

from src.fee_section_assembler import FeeSection
from src.models import BoundaryEvidence, LogicalDocumentBlock, PhysicalRow


GateDecisionType = Literal["CLEAR", "ESCALATE"]


@dataclass
class GateReason:
    """An explainable escalation or acceptance reason with provenance."""

    code: str
    message: str
    block_ids: List[str] = field(default_factory=list)
    row_ids: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "block_ids": self.block_ids,
            "row_ids": self.row_ids,
            "evidence": self.evidence,
        }


@dataclass
class EvidenceSufficiencyDecision:
    """Result of deterministic evidence sufficiency evaluation."""

    decision: GateDecisionType
    reasons: List[GateReason] = field(default_factory=list)
    inspected_block_ids: List[str] = field(default_factory=list)
    inspected_row_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "inspected_block_ids": self.inspected_block_ids,
            "inspected_row_ids": self.inspected_row_ids,
        }


class EvidenceSufficiencyGate:
    """Conservatively decide whether deterministic evidence is sufficient."""

    CONTINUATION_PREFIXES = (
        "with min.",
        "with max.",
        "min.",
        "max.",
        "minimum of",
        "maximum of",
        "plus ",
    )

    def evaluate(
        self,
        blocks: Sequence[LogicalDocumentBlock],
        fee_sections: Sequence[FeeSection],
        boundary_decisions: Optional[Iterable[Any]] = None,
        boundary_evidence: Optional[Iterable[BoundaryEvidence]] = None,
    ) -> EvidenceSufficiencyDecision:
        """Evaluate existing deterministic output without changing it."""
        block_map = {block.block_id: block for block in blocks}
        reasons: List[GateReason] = []

        inspected_block_ids = [block.block_id for block in blocks]
        inspected_row_ids = [
            row.row_id
            for block in blocks
            for row in block.physical_rows
        ]

        boundary_decision_list = list(boundary_decisions or [])
        boundary_evidence_list = list(boundary_evidence or [])

        self._check_boundaries(
            boundary_decision_list,
            boundary_evidence_list,
            blocks,
            reasons,
        )
        self._check_boundary_evidence(
            boundary_evidence_list,
            blocks,
            reasons,
        )
        self._check_blocks(blocks, reasons)
        self._check_footnotes(blocks, reasons)
        self._check_fee_sections(fee_sections, block_map, reasons)
        self._check_unrepresented_structures(blocks, fee_sections, reasons)

        return EvidenceSufficiencyDecision(
            decision="ESCALATE" if reasons else "CLEAR",
            reasons=reasons,
            inspected_block_ids=inspected_block_ids,
            inspected_row_ids=inspected_row_ids,
        )

    @staticmethod
    def _check_boundaries(
        boundary_decisions: Sequence[Any],
        boundary_evidence: Sequence[BoundaryEvidence],
        blocks: Sequence[LogicalDocumentBlock],
        reasons: List[GateReason],
    ) -> None:
        for index, decision in enumerate(boundary_decisions):
            evidence = (
                boundary_evidence[index]
                if index < len(boundary_evidence)
                else None
            )
            block_ids, row_ids, provenance = EvidenceSufficiencyGate._boundary_context(
                evidence,
                blocks,
            )
            if getattr(decision, "decision", None) == "AMBIGUOUS":
                reasons.append(
                    GateReason(
                        code="ambiguous_boundary",
                        message="A structural boundary remains ambiguous.",
                        block_ids=block_ids,
                        row_ids=row_ids,
                        evidence={
                            **provenance,
                            "supporting_evidence": getattr(
                                decision, "supporting_evidence", []
                            ),
                            "unresolved_evidence": getattr(
                                decision, "unresolved_evidence", []
                            ),
                            "reason": getattr(decision, "reason", ""),
                        },
                    )
                )
            if getattr(decision, "conflicting_evidence", []):
                reasons.append(
                    GateReason(
                        code="conflicting_structural_evidence",
                        message="A boundary contains conflicting structural evidence.",
                        block_ids=block_ids,
                        row_ids=row_ids,
                        evidence={
                            **provenance,
                            "conflicting_evidence": decision.conflicting_evidence,
                            "reason": getattr(decision, "reason", ""),
                        },
                    )
                )

    @staticmethod
    def _check_boundary_evidence(
        boundary_evidence: Sequence[BoundaryEvidence],
        blocks: Sequence[LogicalDocumentBlock],
        reasons: List[GateReason],
    ) -> None:
        for evidence in boundary_evidence:
            invalid = []
            if not 0.0 <= evidence.horizontal_overlap <= 1.0:
                invalid.append("horizontal_overlap_out_of_range")
            if not 0.0 <= evidence.left_margin_similarity <= 1.0:
                invalid.append("left_margin_similarity_out_of_range")
            if evidence.visual_span_count_a < 0 or evidence.visual_span_count_b < 0:
                invalid.append("negative_visual_span_count")
            if invalid:
                block_ids, row_ids, provenance = EvidenceSufficiencyGate._boundary_context(
                    evidence,
                    blocks,
                )
                reasons.append(
                    GateReason(
                        code="contradictory_physical_visual_evidence",
                        message="Boundary measurements contain contradictory values.",
                        block_ids=block_ids,
                        row_ids=row_ids,
                        evidence={**provenance, "issues": invalid},
                    )
                )

    @staticmethod
    def _boundary_context(
        evidence: Optional[BoundaryEvidence],
        blocks: Sequence[LogicalDocumentBlock],
    ) -> tuple[List[str], List[str], Dict[str, Any]]:
        if evidence is None:
            return [], [], {}

        provenance: Dict[str, Any] = {
            "page_number": evidence.page_number,
            "row_a_index": evidence.row_a_index,
            "row_b_index": evidence.row_b_index,
            "row_a_text": evidence.row_a_text,
            "row_b_text": evidence.row_b_text,
        }

        page_rows = [
            (block.block_id, row)
            for block in blocks
            for row in block.physical_rows
            if row.page_number == evidence.page_number
        ]
        page_rows.sort(key=lambda item: item[1].coordinates["y1"])

        indexes = (evidence.row_a_index, evidence.row_b_index)
        if any(index < 0 or index >= len(page_rows) for index in indexes):
            return [], [], provenance

        row_a_block, row_a = page_rows[evidence.row_a_index]
        row_b_block, row_b = page_rows[evidence.row_b_index]
        if row_a.text != evidence.row_a_text or row_b.text != evidence.row_b_text:
            return [], [], provenance

        return (
            list(dict.fromkeys([row_a_block, row_b_block])),
            [row_a.row_id, row_b.row_id],
            {
                **provenance,
                "row_a_id": row_a.row_id,
                "row_b_id": row_b.row_id,
                "row_a_coordinates": row_a.coordinates,
                "row_b_coordinates": row_b.coordinates,
            },
        )

    @staticmethod
    def _check_footnotes(
        blocks: Sequence[LogicalDocumentBlock],
        reasons: List[GateReason],
    ) -> None:
        for block in blocks:
            for row in block.physical_rows:
                text = row.text.lower()
                if re.match(r"^\d+\s+", text) and any(
                    marker in text for marker in ("€", "eur", "usd", "gbp", "chf")
                ):
                    reasons.append(
                        GateReason(
                            code="unresolved_footnote_association",
                            message="A numbered footnote contains an amount requiring scope review.",
                            block_ids=[block.block_id],
                            row_ids=[row.row_id],
                            evidence={"row_text": row.text},
                        )
                    )

    def _check_blocks(
        self,
        blocks: Sequence[LogicalDocumentBlock],
        reasons: List[GateReason],
    ) -> None:
        for block in blocks:
            if not block.physical_rows:
                reasons.append(
                    GateReason(
                        code="missing_physical_evidence",
                        message="A logical block has no physical rows.",
                        block_ids=[block.block_id],
                    )
                )
                continue

            invalid_rows = [
                row for row in block.physical_rows
                if self._invalid_coordinates(row)
            ]
            if invalid_rows:
                reasons.append(
                    GateReason(
                        code="contradictory_physical_evidence",
                        message="A physical row has invalid coordinates.",
                        block_ids=[block.block_id],
                        row_ids=[row.row_id for row in invalid_rows],
                        evidence={
                            "coordinates": [row.coordinates for row in invalid_rows]
                        },
                    )
                )

    def _check_fee_sections(
        self,
        fee_sections: Sequence[FeeSection],
        block_map: Dict[str, LogicalDocumentBlock],
        reasons: List[GateReason],
    ) -> None:
        for section in fee_sections:
            for item in section.fee_items:
                item_blocks = [
                    block_map[block_id]
                    for block_id in item.source_blocks
                    if block_id in block_map
                ]
                item_rows = [
                    row
                    for block in item_blocks
                    for row in block.physical_rows
                ]
                block_ids = list(item.source_blocks)
                row_ids = [row.row_id for row in item_rows]

                if not item_blocks:
                    reasons.append(
                        GateReason(
                            code="missing_physical_evidence",
                            message="A fee item has no resolvable source block.",
                            block_ids=block_ids,
                        )
                    )
                    continue

                if item.fee_text is None and not item.tiers:
                    reasons.append(
                        GateReason(
                            code="unsupported_required_fee_field",
                            message="A fee item has no supported fee value or tiers.",
                            block_ids=block_ids,
                            row_ids=row_ids,
                            evidence={"description": item.description},
                        )
                    )

                missing_visual_rows = [
                    row for row in item_rows if not row.visual_spans
                ]
                if missing_visual_rows:
                    reasons.append(
                        GateReason(
                            code="missing_visual_evidence",
                            message="Fee evidence lacks VisualSpan data for one or more source rows.",
                            block_ids=block_ids,
                            row_ids=[row.row_id for row in missing_visual_rows],
                        )
                    )

                self._check_associations(
                    item,
                    item_blocks,
                    block_ids,
                    row_ids,
                    reasons,
                )

        self._check_cross_references(fee_sections, block_map, reasons)

    def _check_unrepresented_structures(
        self,
        blocks: Sequence[LogicalDocumentBlock],
        fee_sections: Sequence[FeeSection],
        reasons: List[GateReason],
    ) -> None:
        represented_blocks = {
            block_id
            for section in fee_sections
            for item in section.fee_items
            for block_id in item.source_blocks
        }

        for block in blocks:
            if block.block_id in represented_blocks:
                continue

            rows = [self._normalize(row.text) for row in block.physical_rows]
            continuation_rows = [
                row
                for row in block.physical_rows
                if self._is_continuation(self._normalize(row.text))
            ]
            if continuation_rows:
                reasons.append(
                    GateReason(
                        code="unresolved_parent_continuation",
                        message="A continuation row has no deterministic parent fee.",
                        block_ids=[block.block_id],
                        row_ids=[row.row_id for row in continuation_rows],
                    )
                )

            has_tier_header = any(
                "amount of transfer" in row and "euro" in row
                for row in rows
            )
            tier_row_count = sum(
                1
                for row in rows
                if re.match(r"^[<>≤≥]?[\d\s.,]+", row) and "€" in row
            )
            if has_tier_header and tier_row_count >= 3:
                reasons.append(
                    GateReason(
                        code="unresolved_tier_table_association",
                        message="A tier-like table has no deterministic fee item.",
                        block_ids=[block.block_id],
                        row_ids=[row.row_id for row in block.physical_rows],
                    )
                )

    def _check_associations(
        self,
        item: Any,
        blocks: Sequence[LogicalDocumentBlock],
        block_ids: List[str],
        row_ids: List[str],
        reasons: List[GateReason],
    ) -> None:
        for block in blocks:
            rows = [self._normalize(row.text) for row in block.physical_rows]
            for index, row_text in enumerate(rows):
                if not self._is_continuation(row_text):
                    continue
                if row_text not in [self._normalize(text) for text in item.continuation_text]:
                    reasons.append(
                        GateReason(
                            code="unresolved_parent_continuation",
                            message="A continuation row is not associated with this fee item.",
                            block_ids=block_ids,
                            row_ids=row_ids,
                            evidence={"row_text": block.physical_rows[index].text},
                        )
                    )

            has_tier_header = any(
                "amount of transfer" in row_text and "euro" in row_text
                for row_text in rows
            )
            has_tier_rows = sum(
                1
                for row_text in rows
                if re.match(r"^[<>≤≥]?[\d\s.,]+", row_text)
                and "€" in row_text
            ) >= 3
            if has_tier_header and has_tier_rows and not item.tiers:
                reasons.append(
                    GateReason(
                        code="unresolved_tier_table_association",
                        message="A tier-like table is not associated with fee tiers.",
                        block_ids=block_ids,
                        row_ids=row_ids,
                    )
                )

    @staticmethod
    def _check_cross_references(
        fee_sections: Sequence[FeeSection],
        block_map: Dict[str, LogicalDocumentBlock],
        reasons: List[GateReason],
    ) -> None:
        for section in fee_sections:
            for block_id in section.source_blocks:
                block = block_map.get(block_id)
                if block is None:
                    continue
                text = block.text_content.lower()
                if "cf standard pricing" in text or "see standard pricing" in text:
                    reasons.append(
                        GateReason(
                            code="unresolved_cross_reference",
                            message="A fee source contains an unresolved pricing cross-reference.",
                            block_ids=[block_id],
                            row_ids=[row.row_id for row in block.physical_rows],
                            evidence={"text": block.text_content},
                        )
                    )

    @staticmethod
    def _invalid_coordinates(row: PhysicalRow) -> bool:
        coordinates = row.coordinates
        return (
            coordinates["x2"] < coordinates["x1"]
            or coordinates["y2"] < coordinates["y1"]
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    def _is_continuation(self, text: str) -> bool:
        return text.startswith(self.CONTINUATION_PREFIXES)
