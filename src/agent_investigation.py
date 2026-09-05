"""Transport contract for future agent investigations.

This module contains no LLM/runtime integration. It separates raw evidence,
deterministic observations, competing hypotheses, and agent conclusions while
keeping source provenance explicit.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence


InvestigationStatus = Literal[
    "RESOLVED",
    "UNRESOLVED",
    "INSUFFICIENT_EVIDENCE",
]

EvidenceRequestType = Literal[
    "page_region",
    "page_image",
    "neighboring_rows",
    "adjacent_page",
    "text_search",
    "repeated_phrase_search",
]

EvidenceSourceKind = Literal[
    "physical_row",
    "visual_span",
    "logical_block",
    "boundary_assessment",
    "fee_item",
    "rendered_region",
    "search_result",
]


class ContractValidationError(ValueError):
    """Raised when an investigation request or result is not supportable."""


@dataclass
class VisualSpanEvidence:
    """Raw visual evidence associated with one physical row."""

    text: str
    font_family: str
    font_size: float
    font_flags: int
    color: int
    bbox: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_flags": self.font_flags,
            "color": self.color,
            "bbox": dict(self.bbox),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualSpanEvidence":
        return cls(
            text=data["text"],
            font_family=data["font_family"],
            font_size=float(data["font_size"]),
            font_flags=int(data["font_flags"]),
            color=int(data["color"]),
            bbox=dict(data["bbox"]),
        )


@dataclass
class PhysicalRowEvidence:
    """Transport snapshot of a raw PhysicalRow and its VisualSpans."""

    row_id: str
    page_number: int
    text: str
    coordinates: Dict[str, float]
    words: List[Dict[str, Any]] = field(default_factory=list)
    visual_spans: List[VisualSpanEvidence] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "page_number": self.page_number,
            "text": self.text,
            "coordinates": dict(self.coordinates),
            "words": list(self.words),
            "visual_spans": [span.to_dict() for span in self.visual_spans],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhysicalRowEvidence":
        return cls(
            row_id=data["row_id"],
            page_number=int(data["page_number"]),
            text=data["text"],
            coordinates=dict(data["coordinates"]),
            words=list(data.get("words", [])),
            visual_spans=[
                VisualSpanEvidence.from_dict(span)
                for span in data.get("visual_spans", [])
            ],
        )


@dataclass
class LogicalBlockEvidence:
    """Deterministic logical-block observation, not an agent conclusion."""

    block_id: str
    page_number: int
    coordinates: Dict[str, float]
    text_content: str
    row_ids: List[str] = field(default_factory=list)
    fee_candidate_ids: List[str] = field(default_factory=list)
    status: Optional[str] = None
    confidence_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "page_number": self.page_number,
            "coordinates": dict(self.coordinates),
            "text_content": self.text_content,
            "row_ids": list(self.row_ids),
            "fee_candidate_ids": list(self.fee_candidate_ids),
            "status": self.status,
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogicalBlockEvidence":
        return cls(
            block_id=data["block_id"],
            page_number=int(data["page_number"]),
            coordinates=dict(data["coordinates"]),
            text_content=data["text_content"],
            row_ids=list(data.get("row_ids", [])),
            fee_candidate_ids=list(data.get("fee_candidate_ids", [])),
            status=data.get("status"),
            confidence_score=data.get("confidence_score"),
        )


@dataclass
class BoundaryAssessment:
    """Paired deterministic boundary evidence and decision."""

    page_number: int
    row_a_index: int
    row_b_index: int
    row_a_id: Optional[str]
    row_b_id: Optional[str]
    row_a_text: str
    row_b_text: str
    row_a_coordinates: Optional[Dict[str, float]]
    row_b_coordinates: Optional[Dict[str, float]]
    decision: Literal["JOIN", "SPLIT", "AMBIGUOUS"]
    decision_reason: str
    supporting_evidence: List[str] = field(default_factory=list)
    conflicting_evidence: List[str] = field(default_factory=list)
    unresolved_evidence: List[str] = field(default_factory=list)
    observations: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "row_a_index": self.row_a_index,
            "row_b_index": self.row_b_index,
            "row_a_id": self.row_a_id,
            "row_b_id": self.row_b_id,
            "row_a_text": self.row_a_text,
            "row_b_text": self.row_b_text,
            "row_a_coordinates": self.row_a_coordinates,
            "row_b_coordinates": self.row_b_coordinates,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "supporting_evidence": list(self.supporting_evidence),
            "conflicting_evidence": list(self.conflicting_evidence),
            "unresolved_evidence": list(self.unresolved_evidence),
            "observations": dict(self.observations),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoundaryAssessment":
        return cls(
            page_number=int(data["page_number"]),
            row_a_index=int(data["row_a_index"]),
            row_b_index=int(data["row_b_index"]),
            row_a_id=data.get("row_a_id"),
            row_b_id=data.get("row_b_id"),
            row_a_text=data["row_a_text"],
            row_b_text=data["row_b_text"],
            row_a_coordinates=data.get("row_a_coordinates"),
            row_b_coordinates=data.get("row_b_coordinates"),
            decision=data["decision"],
            decision_reason=data["decision_reason"],
            supporting_evidence=list(data.get("supporting_evidence", [])),
            conflicting_evidence=list(data.get("conflicting_evidence", [])),
            unresolved_evidence=list(data.get("unresolved_evidence", [])),
            observations=dict(data.get("observations", {})),
        )


@dataclass
class InterpretationHypothesis:
    """A competing interpretation retained for investigation."""

    hypothesis_id: str
    kind: str
    summary: str
    source_row_ids: List[str] = field(default_factory=list)
    source_block_ids: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    conflicting_evidence: List[str] = field(default_factory=list)
    status: Literal["candidate", "rejected", "unresolved"] = "candidate"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "kind": self.kind,
            "summary": self.summary,
            "source_row_ids": list(self.source_row_ids),
            "source_block_ids": list(self.source_block_ids),
            "supporting_evidence": list(self.supporting_evidence),
            "conflicting_evidence": list(self.conflicting_evidence),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterpretationHypothesis":
        return cls(
            hypothesis_id=data["hypothesis_id"],
            kind=data["kind"],
            summary=data["summary"],
            source_row_ids=list(data.get("source_row_ids", [])),
            source_block_ids=list(data.get("source_block_ids", [])),
            supporting_evidence=list(data.get("supporting_evidence", [])),
            conflicting_evidence=list(data.get("conflicting_evidence", [])),
            status=data.get("status", "candidate"),
        )


@dataclass
class EvidenceRequest:
    """A bounded request for additional observational evidence."""

    request_id: str
    request_type: EvidenceRequestType
    purpose: str
    page_number: Optional[int] = None
    coordinates: Optional[Dict[str, float]] = None
    row_ids: List[str] = field(default_factory=list)
    query: Optional[str] = None
    max_results: int = 20

    ALLOWED_TYPES = {
        "page_region",
        "page_image",
        "neighboring_rows",
        "adjacent_page",
        "text_search",
        "repeated_phrase_search",
    }

    def validate(self) -> None:
        if self.request_type not in self.ALLOWED_TYPES:
            raise ContractValidationError(
                f"Unsupported observational request type: {self.request_type}"
            )
        if not self.request_id or not self.purpose:
            raise ContractValidationError("Evidence requests require an ID and purpose")
        if not 1 <= self.max_results <= 100:
            raise ContractValidationError("Evidence request max_results must be 1..100")
        if self.request_type in {"page_region", "page_image", "adjacent_page"}:
            if self.page_number is None:
                raise ContractValidationError(
                    f"{self.request_type} requests require page_number"
                )
        if self.request_type == "page_region" and not self.coordinates:
            raise ContractValidationError("page_region requests require coordinates")
        if self.request_type in {"text_search", "repeated_phrase_search"}:
            if not self.query:
                raise ContractValidationError(
                    f"{self.request_type} requests require query"
                )
        if self.request_type == "neighboring_rows" and not self.row_ids:
            raise ContractValidationError(
                "neighboring_rows requests require at least one row ID"
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "request_id": self.request_id,
            "request_type": self.request_type,
            "purpose": self.purpose,
            "page_number": self.page_number,
            "coordinates": self.coordinates,
            "row_ids": list(self.row_ids),
            "query": self.query,
            "max_results": self.max_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceRequest":
        request = cls(
            request_id=data["request_id"],
            request_type=data["request_type"],
            purpose=data["purpose"],
            page_number=data.get("page_number"),
            coordinates=data.get("coordinates"),
            row_ids=list(data.get("row_ids", [])),
            query=data.get("query"),
            max_results=int(data.get("max_results", 20)),
        )
        request.validate()
        return request


@dataclass
class EvidenceReference:
    """A provenance pointer used by deterministic or agent conclusions."""

    source_kind: EvidenceSourceKind
    source_id: Optional[str] = None
    page_number: Optional[int] = None
    row_ids: List[str] = field(default_factory=list)
    block_ids: List[str] = field(default_factory=list)
    coordinates: Optional[Dict[str, float]] = None
    excerpt: Optional[str] = None

    ALLOWED_SOURCE_KINDS = {
        "physical_row",
        "visual_span",
        "logical_block",
        "boundary_assessment",
        "fee_item",
        "rendered_region",
        "search_result",
    }

    def validate(self) -> None:
        if self.source_kind not in self.ALLOWED_SOURCE_KINDS:
            raise ContractValidationError(
                f"Unsupported evidence source kind: {self.source_kind}"
            )
        if not self.source_id and not self.row_ids and not self.block_ids:
            raise ContractValidationError(
                "Evidence references require a source ID, row ID, or block ID"
            )
        if self.page_number is None and not self.block_ids:
            raise ContractValidationError(
                "Evidence references require page_number unless block-scoped"
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "page_number": self.page_number,
            "row_ids": list(self.row_ids),
            "block_ids": list(self.block_ids),
            "coordinates": self.coordinates,
            "excerpt": self.excerpt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceReference":
        reference = cls(
            source_kind=data["source_kind"],
            source_id=data.get("source_id"),
            page_number=data.get("page_number"),
            row_ids=list(data.get("row_ids", [])),
            block_ids=list(data.get("block_ids", [])),
            coordinates=data.get("coordinates"),
            excerpt=data.get("excerpt"),
        )
        reference.validate()
        return reference


@dataclass
class AgentConclusion:
    """An agent interpretation that must remain evidence-backed."""

    conclusion_id: str
    subject: str
    fields: Dict[str, Any]
    evidence_references: List[EvidenceReference] = field(default_factory=list)
    confidence: Optional[float] = None
    status: Literal["resolved", "unresolved"] = "resolved"
    reasoning_summary: Optional[str] = None

    def validate(self) -> None:
        if not self.conclusion_id or not self.subject:
            raise ContractValidationError(
                "Conclusions require conclusion_id and subject"
            )
        if self.status == "resolved" and not self.evidence_references:
            raise ContractValidationError(
                "Resolved conclusions require evidence references"
            )
        for reference in self.evidence_references:
            reference.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "conclusion_id": self.conclusion_id,
            "subject": self.subject,
            "fields": dict(self.fields),
            "evidence_references": [
                reference.to_dict() for reference in self.evidence_references
            ],
            "confidence": self.confidence,
            "status": self.status,
            "reasoning_summary": self.reasoning_summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConclusion":
        conclusion = cls(
            conclusion_id=data["conclusion_id"],
            subject=data["subject"],
            fields=dict(data.get("fields", {})),
            evidence_references=[
                EvidenceReference.from_dict(reference)
                for reference in data.get("evidence_references", [])
            ],
            confidence=data.get("confidence"),
            status=data.get("status", "resolved"),
            reasoning_summary=data.get("reasoning_summary"),
        )
        conclusion.validate()
        return conclusion


@dataclass
class EscalationReason:
    """Structured reason that caused deterministic escalation."""

    code: str
    message: str
    row_ids: List[str] = field(default_factory=list)
    block_ids: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "row_ids": list(self.row_ids),
            "block_ids": list(self.block_ids),
            "evidence": dict(self.evidence),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationReason":
        return cls(
            code=data["code"],
            message=data["message"],
            row_ids=list(data.get("row_ids", [])),
            block_ids=list(data.get("block_ids", [])),
            evidence=dict(data.get("evidence", {})),
        )


@dataclass
class AgentInvestigationRequest:
    """Complete deterministic evidence package for future investigation."""

    request_id: str
    document_id: Optional[str]
    trigger_reasons: List[EscalationReason]
    physical_rows: List[PhysicalRowEvidence]
    logical_blocks: List[LogicalBlockEvidence]
    boundary_assessments: List[BoundaryAssessment]
    fee_items: List[Dict[str, Any]] = field(default_factory=list)
    hypotheses: List[InterpretationHypothesis] = field(default_factory=list)
    permitted_evidence_request_types: List[EvidenceRequestType] = field(
        default_factory=lambda: [
            "page_region",
            "page_image",
            "neighboring_rows",
            "adjacent_page",
            "text_search",
            "repeated_phrase_search",
        ]
    )
    schema_version: str = "1.0"

    def validate(self) -> None:
        if not self.request_id:
            raise ContractValidationError("Investigation requests require request_id")
        for reason in self.trigger_reasons:
            if not reason.code or not reason.message:
                raise ContractValidationError("Escalation reasons require code and message")
        row_ids = {row.row_id for row in self.physical_rows}
        block_ids = {block.block_id for block in self.logical_blocks}
        for block in self.logical_blocks:
            unknown_rows = set(block.row_ids) - row_ids
            if unknown_rows:
                raise ContractValidationError(
                    f"Logical block {block.block_id} references unknown rows"
                )
        for boundary in self.boundary_assessments:
            for row_id in (boundary.row_a_id, boundary.row_b_id):
                if row_id is not None and row_id not in row_ids:
                    raise ContractValidationError(
                        "Boundary assessment references an unknown physical row"
                    )
            for block_id in boundary.observations.get("block_ids", []):
                if block_id not in block_ids:
                    raise ContractValidationError(
                        "Boundary assessment references an unknown logical block"
                    )
        for hypothesis in self.hypotheses:
            if not set(hypothesis.source_row_ids).issubset(row_ids):
                raise ContractValidationError(
                    f"Hypothesis {hypothesis.hypothesis_id} references unknown rows"
                )
            if not set(hypothesis.source_block_ids).issubset(block_ids):
                raise ContractValidationError(
                    f"Hypothesis {hypothesis.hypothesis_id} references unknown blocks"
                )
        invalid_types = set(self.permitted_evidence_request_types) - EvidenceRequest.ALLOWED_TYPES
        if invalid_types:
            raise ContractValidationError(
                f"Unsupported permitted evidence types: {sorted(invalid_types)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "request_id": self.request_id,
            "document_id": self.document_id,
            "trigger_reasons": [reason.to_dict() for reason in self.trigger_reasons],
            "physical_rows": [row.to_dict() for row in self.physical_rows],
            "logical_blocks": [block.to_dict() for block in self.logical_blocks],
            "boundary_assessments": [
                boundary.to_dict() for boundary in self.boundary_assessments
            ],
            "fee_items": list(self.fee_items),
            "hypotheses": [hypothesis.to_dict() for hypothesis in self.hypotheses],
            "permitted_evidence_request_types": list(
                self.permitted_evidence_request_types
            ),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInvestigationRequest":
        request = cls(
            request_id=data["request_id"],
            document_id=data.get("document_id"),
            trigger_reasons=[
                EscalationReason.from_dict(reason)
                for reason in data.get("trigger_reasons", [])
            ],
            physical_rows=[
                PhysicalRowEvidence.from_dict(row)
                for row in data.get("physical_rows", [])
            ],
            logical_blocks=[
                LogicalBlockEvidence.from_dict(block)
                for block in data.get("logical_blocks", [])
            ],
            boundary_assessments=[
                BoundaryAssessment.from_dict(boundary)
                for boundary in data.get("boundary_assessments", [])
            ],
            fee_items=list(data.get("fee_items", [])),
            hypotheses=[
                InterpretationHypothesis.from_dict(hypothesis)
                for hypothesis in data.get("hypotheses", [])
            ],
            permitted_evidence_request_types=list(
                data.get("permitted_evidence_request_types", [])
            ),
            schema_version=data.get("schema_version", "1.0"),
        )
        request.validate()
        return request


@dataclass
class AgentInvestigationResult:
    """Evidence-backed result of a future investigation."""

    request_id: str
    status: InvestigationStatus
    conclusions: List[AgentConclusion] = field(default_factory=list)
    alternatives: List[InterpretationHypothesis] = field(default_factory=list)
    unresolved_reason: Optional[str] = None
    missing_or_conflicting_evidence: List[str] = field(default_factory=list)
    follow_up_requests: List[EvidenceRequest] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.request_id:
            raise ContractValidationError("Investigation results require request_id")
        if self.status not in {
            "RESOLVED",
            "UNRESOLVED",
            "INSUFFICIENT_EVIDENCE",
        }:
            raise ContractValidationError(f"Unsupported investigation status: {self.status}")

        for conclusion in self.conclusions:
            conclusion.validate()
        for hypothesis in self.alternatives:
            if not hypothesis.summary:
                raise ContractValidationError("Alternative hypotheses require summaries")
        for request in self.follow_up_requests:
            request.validate()

        if self.status == "RESOLVED":
            if not self.conclusions:
                raise ContractValidationError(
                    "RESOLVED results require at least one conclusion"
                )
            if any(conclusion.status != "resolved" for conclusion in self.conclusions):
                raise ContractValidationError(
                    "RESOLVED results cannot contain unresolved conclusions"
                )
        elif self.status == "UNRESOLVED":
            if not self.alternatives and not self.unresolved_reason:
                raise ContractValidationError(
                    "UNRESOLVED results require alternatives or unresolved_reason"
                )
        elif not self.missing_or_conflicting_evidence:
            raise ContractValidationError(
                "INSUFFICIENT_EVIDENCE results require missing/conflicting evidence"
            )

    def validate_against(self, request: AgentInvestigationRequest) -> None:
        """Validate result references against the originating request evidence."""
        self.validate()
        request.validate()

        if self.request_id != request.request_id:
            raise ContractValidationError(
                "Investigation result does not belong to the supplied request"
            )

        rows = {row.row_id: row for row in request.physical_rows}
        blocks = {block.block_id: block for block in request.logical_blocks}
        boundaries = request.boundary_assessments
        fee_item_ids = {
            item.get("fee_item_id") or item.get("id")
            for item in request.fee_items
            if item.get("fee_item_id") or item.get("id")
        }

        for conclusion in self.conclusions:
            for reference in conclusion.evidence_references:
                self._validate_reference_against(
                    reference,
                    rows,
                    blocks,
                    boundaries,
                    fee_item_ids,
                )

    @staticmethod
    def _validate_reference_against(
        reference: EvidenceReference,
        rows: Dict[str, PhysicalRowEvidence],
        blocks: Dict[str, LogicalBlockEvidence],
        boundaries: Sequence[BoundaryAssessment],
        fee_item_ids: set,
    ) -> None:
        reference.validate()

        if reference.source_kind in {"rendered_region", "search_result"}:
            raise ContractValidationError(
                "Reference source is not present in the originating request"
            )

        unknown_rows = set(reference.row_ids) - set(rows)
        if unknown_rows:
            raise ContractValidationError(
                f"Reference contains unknown physical rows: {sorted(unknown_rows)}"
            )

        unknown_blocks = set(reference.block_ids) - set(blocks)
        if unknown_blocks:
            raise ContractValidationError(
                f"Reference contains unknown logical blocks: {sorted(unknown_blocks)}"
            )

        if reference.source_kind == "physical_row":
            source_row_id = reference.source_id
            if source_row_id and source_row_id not in rows:
                raise ContractValidationError(
                    f"Reference contains unknown physical row: {source_row_id}"
                )
            if not reference.row_ids and not source_row_id:
                raise ContractValidationError(
                    "Physical-row references require a physical row ID"
                )
            referenced_rows = [rows[row_id] for row_id in reference.row_ids]
            if source_row_id and source_row_id not in reference.row_ids:
                referenced_rows.append(rows[source_row_id])
            AgentInvestigationResult._validate_page_and_coordinates(
                reference,
                referenced_rows,
            )
            return

        if reference.source_kind == "visual_span":
            if not reference.row_ids:
                raise ContractValidationError(
                    "Visual-span references require source row IDs"
                )
            referenced_rows = [rows[row_id] for row_id in reference.row_ids]
            if reference.coordinates and not any(
                reference.coordinates == span.bbox
                for row in referenced_rows
                for span in row.visual_spans
            ):
                raise ContractValidationError(
                    "Visual-span coordinates are absent from the referenced rows"
                )
            AgentInvestigationResult._validate_page_and_coordinates(
                reference,
                referenced_rows,
                check_coordinates=False,
            )
            return

        if reference.source_kind == "logical_block":
            source_block_id = reference.source_id
            if source_block_id and source_block_id not in blocks:
                raise ContractValidationError(
                    f"Reference contains unknown logical block: {source_block_id}"
                )
            if not reference.block_ids and not source_block_id:
                raise ContractValidationError(
                    "Logical-block references require a logical block ID"
                )
            referenced_blocks = [blocks[block_id] for block_id in reference.block_ids]
            if source_block_id and source_block_id not in reference.block_ids:
                referenced_blocks.append(blocks[source_block_id])
            AgentInvestigationResult._validate_page_and_coordinates(
                reference,
                referenced_blocks,
            )
            return

        if reference.source_kind == "boundary_assessment":
            matching_boundaries = [
                boundary
                for boundary in boundaries
                if AgentInvestigationResult._boundary_matches(
                    reference,
                    boundary,
                )
            ]
            if not matching_boundaries:
                raise ContractValidationError(
                    "Reference does not identify a boundary assessment in the request"
                )
            return

        if reference.source_kind == "fee_item":
            if not reference.source_id or reference.source_id not in fee_item_ids:
                raise ContractValidationError(
                    "Reference does not identify a fee item in the request"
                )
            return

    @staticmethod
    def _validate_page_and_coordinates(
        reference: EvidenceReference,
        sources: Sequence[Any],
        check_coordinates: bool = True,
    ) -> None:
        if reference.page_number is not None and any(
            source.page_number != reference.page_number for source in sources
        ):
            raise ContractValidationError(
                "Reference page_number does not match its source evidence"
            )
        if check_coordinates and reference.coordinates is not None and any(
            source.coordinates != reference.coordinates for source in sources
        ):
            raise ContractValidationError(
                "Reference coordinates do not match its source evidence"
            )

    @staticmethod
    def _boundary_matches(
        reference: EvidenceReference,
        boundary: BoundaryAssessment,
    ) -> bool:
        if reference.page_number != boundary.page_number:
            return False
        if reference.source_id:
            boundary_id = (
                f"{boundary.page_number}:"
                f"{boundary.row_a_index}:{boundary.row_b_index}"
            )
            if reference.source_id != boundary_id:
                return False
        expected_rows = {boundary.row_a_id, boundary.row_b_id} - {None}
        if reference.row_ids and set(reference.row_ids) != expected_rows:
            return False
        if reference.coordinates:
            if reference.coordinates != boundary.row_a_coordinates:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "request_id": self.request_id,
            "status": self.status,
            "conclusions": [conclusion.to_dict() for conclusion in self.conclusions],
            "alternatives": [
                alternative.to_dict() for alternative in self.alternatives
            ],
            "unresolved_reason": self.unresolved_reason,
            "missing_or_conflicting_evidence": list(
                self.missing_or_conflicting_evidence
            ),
            "follow_up_requests": [
                request.to_dict() for request in self.follow_up_requests
            ],
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInvestigationResult":
        result = cls(
            request_id=data["request_id"],
            status=data["status"],
            conclusions=[
                AgentConclusion.from_dict(conclusion)
                for conclusion in data.get("conclusions", [])
            ],
            alternatives=[
                InterpretationHypothesis.from_dict(alternative)
                for alternative in data.get("alternatives", [])
            ],
            unresolved_reason=data.get("unresolved_reason"),
            missing_or_conflicting_evidence=list(
                data.get("missing_or_conflicting_evidence", [])
            ),
            follow_up_requests=[
                EvidenceRequest.from_dict(request)
                for request in data.get("follow_up_requests", [])
            ],
            limitations=list(data.get("limitations", [])),
        )
        result.validate()
        return result
