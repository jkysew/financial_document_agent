"""
Data models for Financial Document Agent v3
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid
import hashlib

class Status(Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED = "UNSUPPORTED"

@dataclass
class VisualSpan:
    """Represents a visual span from PDF with font and layout information"""
    text: str
    font_family: str
    font_size: float
    font_flags: int
    color: int
    bbox: Dict[str, float]  # {x0, y0, x1, y1}

@dataclass
class PhysicalRow:
    """Represents a physical row from the PDF with coordinates and text"""
    page_number: int
    coordinates: Dict[str, float]
    text: str
    words: List[Dict[str, Any]]
    visual_spans: List[VisualSpan] = None
    row_id: str = None

    def __post_init__(self):
        if self.visual_spans is None:
            self.visual_spans = []
        if self.row_id is None:
            self.row_id = self._generate_deterministic_row_id()

    def _generate_deterministic_row_id(self) -> str:
        """Generate a deterministic row ID based on page number, coordinates and text"""
        data = f"{self.page_number}_{self.coordinates}_{self.text}"
        hash_object = hashlib.md5(data.encode())
        hex_dig = hash_object.hexdigest()[:12]
        return f"row_{self.page_number}_{hex_dig}"


@dataclass
class EvidenceSource:
    """Raw evidence source that can be referenced"""
    source_type: str  # "text", "image", "coordinate_region"
    page_number: int
    coordinates: Dict[str, float]  # {x1, y1, x2, y2}
    content: str  # Raw content (text or image data)
    context: str  # Surrounding text context
    evidence_id: str = None

    def __post_init__(self):
        if self.evidence_id is None:
            self.evidence_id = str(uuid.uuid4())


@dataclass
class FeeCandidate:
    """A fee candidate extracted from a logical document block"""
    description: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    unit: Optional[str] = None
    vat_status: str = "unknown"  # "included", "additional", "unknown"
    pricing_type: str = "fixed"  # "fixed", "variable", "reinvoicing", "cost"
    references: List[str] = None
    constraints: List[Dict[str, Any]] = None
    source_page: int = 0
    source_coordinates: Dict[str, float] = None
    evidence_text: str = ""
    status: Status = Status.AMBIGUOUS
    confidence_score: float = 0.0
    candidate_id: str = None

    def __post_init__(self):
        if self.references is None:
            self.references = []
        if self.constraints is None:
            self.constraints = []
        if self.source_coordinates is None:
            self.source_coordinates = {}
        if self.candidate_id is None:
            self.candidate_id = str(uuid.uuid4())


@dataclass
class LogicalDocumentBlock:
    """Logical unit that may contain multiple physical rows and fee candidates"""
    block_id: str
    type: str  # "fee_section", "description_block", "pricing_rule", etc.
    page_number: int
    coordinates: Dict[str, float]  # {x1, y1, x2, y2}
    text_content: str
    physical_rows: List[PhysicalRow]
    evidence_sources: List[EvidenceSource]
    fee_candidates: List[FeeCandidate]
    status: Status = Status.AMBIGUOUS
    ambiguities: List[str] = None
    confidence_score: float = 0.0
    interpretation_notes: List[str] = None

    def __post_init__(self):
        if self.ambiguities is None:
            self.ambiguities = []
        if self.interpretation_notes is None:
            self.interpretation_notes = []
        if self.fee_candidates is None:
            self.fee_candidates = []
        if self.evidence_sources is None:
            self.evidence_sources = []
        if self.physical_rows is None:
            self.physical_rows = []
        # Fixed mutable defaults for references and constraints in FeeCandidate
        # This is already handled in FeeCandidate's __post_init__

@dataclass
class BoundaryEvidence:
    """Deterministic evidence describing an adjacent PhysicalRow boundary."""

    page_number: int
    row_a_index: int
    row_b_index: int
    row_a_text: str
    row_b_text: str

    raw_vertical_gap: float
    horizontal_overlap: float
    left_margin_delta: float
    left_margin_similarity: float

    font_size_difference: float
    font_size_similarity: float
    font_family_similarity: float
    bold_relationship: str

    visual_span_count_a: int
    visual_span_count_b: int
    visual_span_composition_a: Dict[str, Any]
    visual_span_composition_b: Dict[str, Any]

    page_median_gap: float
    robust_gap_spread: float
    local_gap_ratio: float

    neighborhood_evidence: Dict[str, Any]