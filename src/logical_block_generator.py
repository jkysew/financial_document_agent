"""
Logical block generator for Financial Document Agent v3
Creates logical document blocks from physical evidence using deterministic grouping
"""

from typing import List, Dict, Any, Optional
from src.models import LogicalDocumentBlock, PhysicalRow, EvidenceSource
from src.models import Status


# ── helpers ───────────────────────────────────────────────────────────────

def _dominant_font_size(row: PhysicalRow) -> float:
    """Return the font size of the first visual span in the row, or 0 if unavailable.

    Handles common attribute-names and non-numeric values defensively.
    """
    spans = getattr(row, "visual_spans", None)
    if not spans:
        return 0.0
    for s in spans:
        size = getattr(s, "font_size", None)
        if size is not None:
            try:
                val = float(size)
                if val > 0:
                    return val
            except (TypeError, ValueError):
                continue
    return 0.0


def _font_families(row: PhysicalRow) -> List[str]:
    """Return the list of font_family strings from visual spans in the row.

    Looks for both 'font_family' and 'fontName' attribute conventions.
    Returns an empty list when no spans or families are found.
    """
    spans = getattr(row, "visual_spans", None)
    if not spans:
        return []
    families: List[str] = []
    for s in spans:
        fam = getattr(s, "font_family", None) or getattr(s, "fontName", None)
        if fam and isinstance(fam, str) and fam.strip():
            families.append(fam.strip())
    return families


def _is_bold(row: PhysicalRow) -> bool:
    """Heuristic boldness indicator from visual span data.

    font_flags bit 5 (value 32) traditionally indicates bold in PDFToText.
    Also treats a row as potentially bold if any span contains 'Bold' in its
    font_family or fontName attribute.
    """
    spans = getattr(row, "visual_spans", None)
    if not spans:
        return False
    for s in spans:
        flags = getattr(s, "font_flags", 0)
        try:
            if int(flags) & 32:
                return True
        except (TypeError, ValueError):
            pass
        fam = getattr(s, "font_family", "") or getattr(s, "fontName", "")
        if isinstance(fam, str) and ("Bold" in fam or "bold" in fam):
            return True
    return False


def _compute_adaptive_gap(rows: List[PhysicalRow]) -> float:
    """Derive a normal vertical gap without letting a clear gap cluster dominate."""
    if len(rows) < 2:
        return 30.0
    gaps = []
    for i in range(1, len(rows)):
        gap = rows[i].coordinates['y1'] - rows[i - 1].coordinates['y2']
        gaps.append(gap)
    if not gaps:
        return 30.0
    gaps_sorted = sorted(gaps)

    if len(gaps_sorted) >= 2:
        jumps = [
            gaps_sorted[index + 1] - gaps_sorted[index]
            for index in range(len(gaps_sorted) - 1)
        ]
        largest_jump_index = max(range(len(jumps)), key=jumps.__getitem__)
        lower_gap = gaps_sorted[largest_jump_index]
        upper_gap = gaps_sorted[largest_jump_index + 1]

        if (
            upper_gap >= max(lower_gap * 2.0, lower_gap + 5.0)
        ):
            return float(lower_gap)

    n = len(gaps_sorted)
    median_gap = (
        gaps_sorted[n // 2]
        if n % 2 == 1
        else (gaps_sorted[n // 2 - 1] + gaps_sorted[n // 2]) / 2.0
    )
    return float(median_gap)


def compute_row_relationship(prev_row: PhysicalRow, curr_row: PhysicalRow) -> Dict[str, Any]:
    """Calculate feature values describing the relationship between two adjacent physical rows.

    Returns a dict with inspectable feature values:
        vertical_gap: float - pixel distance between prev bottom and curr top (negative = overlap)
        horizontal_overlap: float - x-axis overlap fraction in [0, 1] (1 = fully overlapping relative to narrower span)
        left_margin_similarity: float - similarity of left margins in [0, 1] (1 = identical, 0 = no shared width)
        font_size_similarity: float - similarity of dominant font sizes in [0, 1] (1 = identical, 0.5 when both zero)
        font_family_similarity: float - Jaccard similarity of font families in [0, 1] (1 = identical, 1.0 when both empty)
        bold_similarity: float - similarity of boldness indicators in [0, 1] (1 = same state, 0 = different)

    Defensive improvements:
    - Zero-width / zero-height rows are handled without division-by-zero
    - When both font sizes are zero (missing), returns 0.5 to signal "equal but unknown"
    - Left-margin similarity degrades gracefully when combined width is tiny (< 1 pt)
    """
    # ── vertical gap ──────────────────────────────────────────────────────
    vertical_gap = curr_row.coordinates['y1'] - prev_row.coordinates['y2']

    # ── horizontal overlap ────────────────────────────────────────────────
    x1_prev, x2_prev = prev_row.coordinates['x1'], prev_row.coordinates['x2']
    x1_curr, x2_curr = curr_row.coordinates['x1'], curr_row.coordinates['x2']
    span_prev = abs(x2_prev - x1_prev)
    span_curr = abs(x2_curr - x1_curr)
    overlap_x = max(0.0, min(x2_prev, x2_curr) - max(x1_prev, x1_curr))
    denom_span = min(span_prev, span_curr)
    horizontal_overlap = overlap_x / denom_span if denom_span >= 1e-9 else (1.0 if (denom_span == 0.0 and abs(x1_prev - x1_curr) < 1e-6) else 0.0)

    # ── left margin similarity ────────────────────────────────────────────
    margin_delta = abs(x1_prev - x1_curr)
    combined_width = max(abs(x2_prev - x1_prev), abs(x2_curr - x1_curr))
    if combined_width < 1e-6:
        # Both spans are degenerate (near-zero width); identical only if x1 matches
        left_margin_sim = 1.0 if margin_delta < 1e-6 else 0.0
    else:
        left_margin_sim = max(0.0, 1.0 - margin_delta / combined_width)

    # ── font-size similarity ──────────────────────────────────────────────
    prev_font_size = _dominant_font_size(prev_row)
    curr_font_size = _dominant_font_size(curr_row)
    if prev_font_size == 0.0 and curr_font_size == 0.0:
        # Both missing — report "equal but unknown" rather than degenerate similarity
        font_size_sim = 0.5
    else:
        denom_fs = max(prev_font_size, curr_font_size)
        font_size_sim = 1.0 - abs(prev_font_size - curr_font_size) / denom_fs if denom_fs >= 1e-9 else 1.0
        font_size_sim = max(0.0, min(1.0, font_size_sim))

    # ── font-family similarity (Jaccard on sets) ──────────────────────────
    prev_families = frozenset(_font_families(prev_row))
    curr_families = frozenset(_font_families(curr_row))
    union = prev_families | curr_families
    if not union:
        font_family_sim = 1.0  # both empty → identical
    else:
        font_family_sim = len(prev_families & curr_families) / len(union)

    # ── bold similarity ───────────────────────────────────────────────────
    prev_bold = _is_bold(prev_row)
    curr_bold = _is_bold(curr_row)
    bold_sim = 1.0 if prev_bold == curr_bold else 0.0

    return {
        "vertical_gap": vertical_gap,
        "horizontal_overlap": horizontal_overlap,
        "left_margin_similarity": left_margin_sim,
        "font_size_similarity": font_size_sim,
        "font_family_similarity": font_family_sim,
        "bold_similarity": bold_sim,
    }


# ── BlockSplitter class ───────────────────────────────────────────────────

class _BlockSplitter:
    """Deterministic row-grouping using a computed gap threshold."""

    def split(
        self,
        sorted_rows: List[PhysicalRow],
        vertical_spacing_threshold: Optional[float] = None,
    ) -> List[List[PhysicalRow]]:
        if not sorted_rows:
            return []

        if vertical_spacing_threshold is None:
            threshold = max(_compute_adaptive_gap(sorted_rows), 1.0)
        else:
            threshold = vertical_spacing_threshold

        blocks: List[List[PhysicalRow]] = []
        current_block: List[PhysicalRow] = [sorted_rows[0]]

        for i in range(1, len(sorted_rows)):
            prev_row = sorted_rows[i - 1]
            curr_row = sorted_rows[i]
            gap = curr_row.coordinates['y1'] - prev_row.coordinates['y2']

            if gap <= threshold:
                current_block.append(curr_row)
            else:
                blocks.append(current_block)
                current_block = [curr_row]

        if current_block:
            blocks.append(current_block)

        return blocks


# Module-level singleton for convenience
_BLOCK_SPLITTER = _BlockSplitter()


class LogicalBlockGenerator:
    """Generates logical document blocks from physical evidence using deterministic grouping"""
    
    def __init__(self):
        self.blocks: List[LogicalDocumentBlock] = []
        self.block_id_counter = 0
    
    def _calculate_block_coordinates(self, physical_rows: List[PhysicalRow]) -> Dict[str, float]:
        """Calculate bounding coordinates for a block based on its physical rows"""
        if not physical_rows:
            return {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}
        
        x_coords = [row.coordinates['x1'] for row in physical_rows] + [row.coordinates['x2'] for row in physical_rows]
        y_coords = [row.coordinates['y1'] for row in physical_rows] + [row.coordinates['y2'] for row in physical_rows]
        
        return {
            'x1': min(x_coords),
            'y1': min(y_coords),
            'x2': max(x_coords),
            'y2': max(y_coords)
        }
    
    def _calculate_text_content(self, physical_rows: List[PhysicalRow]) -> str:
        """Calculate text content from physical rows while preserving order"""
        return " ".join(row.text for row in physical_rows)
    
    def create_logical_block(self, page_number: int, coordinates: Dict[str, float],
                           text_content: str, physical_rows: List[PhysicalRow], 
                           block_type: str = "logical_block") -> LogicalDocumentBlock:
        """Create a logical document block from physical rows"""
        block_id = f"block_{self.block_id_counter:03d}"
        self.block_id_counter += 1
        
        # Create evidence sources for each physical row
        evidence_sources = []
        for row in physical_rows:
            evidence = EvidenceSource(
                source_type="text",
                page_number=row.page_number,
                coordinates=row.coordinates,
                content=row.text,
                context=text_content
            )
            evidence_sources.append(evidence)
        
        block = LogicalDocumentBlock(
            block_id=block_id,
            type=block_type,
            page_number=page_number,
            coordinates=coordinates,
            text_content=text_content,
            physical_rows=physical_rows,
            evidence_sources=evidence_sources,
            fee_candidates=[],
            status=Status.AMBIGUOUS
        )
        
        self.blocks.append(block)
        return block
    
    def get_blocks_for_page(self, page_number: int) -> List[LogicalDocumentBlock]:
        """Get all logical blocks for a specific page"""
        return [block for block in self.blocks if block.page_number == page_number]
    
    def get_all_blocks(self) -> List[LogicalDocumentBlock]:
        """Get all logical blocks"""
        return self.blocks
    
    def create_blocks_from_rows(self, physical_rows: List[PhysicalRow]) -> List[LogicalDocumentBlock]:
        """Create logical blocks from a list of physical rows using deterministic grouping"""
        if not physical_rows:
            return []
        
        # Group rows by page first
        pages = {}
        for row in physical_rows:
            if row.page_number not in pages:
                pages[row.page_number] = []
            pages[row.page_number].append(row)
        
        # Process each page separately
        all_blocks = []
        for page_number, page_rows in pages.items():
            # Sort rows by y-coordinate (top to bottom) to maintain reading order
            sorted_rows = sorted(page_rows, key=lambda r: r.coordinates['y1'])
            
            # Group rows into blocks based on vertical spacing
            blocks = self._group_rows_into_blocks(sorted_rows)
            
            # Create logical blocks for each group of physical rows
            for block_rows in blocks:
                coordinates = self._calculate_block_coordinates(block_rows)
                text_content = self._calculate_text_content(block_rows)
                
                # Use neutral block type - no semantic interpretation
                logical_block = self.create_logical_block(
                    page_number=page_number,
                    coordinates=coordinates,
                    text_content=text_content,
                    physical_rows=block_rows,
                    block_type="logical_block"
                )
                all_blocks.append(logical_block)
        
        return all_blocks
    
    def _group_rows_into_blocks(
        self,
        sorted_rows: List[PhysicalRow],
        vertical_spacing_threshold: Optional[float] = None,
    ) -> List[List[PhysicalRow]]:
        """Group physical rows into logical blocks using a document-adaptive gap threshold.

        An explicit threshold preserves the legacy behavior; when omitted, the
        threshold is derived from the row gaps.
        """
        return _BLOCK_SPLITTER.split(
            sorted_rows,
            vertical_spacing_threshold=vertical_spacing_threshold,
        )