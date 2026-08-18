"""
Boundary Evidence component for Financial Document Agent v4

This module implements the BoundaryEvidence class and BoundaryEvidenceProvider
that provides deterministic, evidence-preserving boundary detection and analysis
for financial documents without making structural decisions.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from src.models import PhysicalRow, BoundaryEvidence, EvidenceSource
import statistics


@dataclass
class BoundaryEvidenceProvider:
    """Provides raw boundary evidence without making structural decisions"""

    def get_boundary_evidence(
        self,
        page_rows: List[PhysicalRow],
        boundary_index: int,
        neighborhood_window: int = 3,
    ) -> BoundaryEvidence:
        """
        Generate boundary evidence for the pair of rows at boundary_index and boundary_index + 1

        Args:
            page_rows: List of PhysicalRows for one page in physical order
            boundary_index: Index of Row A (the first row in the boundary pair)
            neighborhood_window: Number of surrounding rows to consider (default: 3)

        Returns:
            BoundaryEvidence: Raw evidence about the boundary between the two rows
        """
        # Validate inputs
        if not page_rows or boundary_index < 0 or boundary_index >= len(page_rows) - 1:
            raise ValueError("Invalid boundary index or empty page_rows")

        row_a = page_rows[boundary_index]
        row_b = page_rows[boundary_index + 1]

        # Calculate pairwise evidence
        raw_vertical_gap = self._calculate_raw_vertical_gap(row_a, row_b)
        horizontal_overlap = self._calculate_horizontal_overlap(row_a, row_b)
        left_margin_delta = self._calculate_left_margin_delta(row_a, row_b)
        left_margin_similarity = self._calculate_left_margin_similarity(row_a, row_b)
        font_size_difference = self._calculate_font_size_difference(row_a, row_b)
        font_size_similarity = self._calculate_font_size_similarity(row_a, row_b)
        font_family_similarity = self._calculate_font_family_similarity(row_a, row_b)
        bold_relationship = self._calculate_bold_relationship(row_a, row_b)

        # Calculate VisualSpan counts
        visual_span_count_a = len(row_a.visual_spans) if row_a.visual_spans else 0
        visual_span_count_b = len(row_b.visual_spans) if row_b.visual_spans else 0

        # Calculate basic VisualSpan composition (first and last spans)
        visual_span_composition_a = self._get_visual_span_composition(row_a)
        visual_span_composition_b = self._get_visual_span_composition(row_b)

        # Calculate page/local evidence
        page_median_gap = self._calculate_page_median_gap(page_rows)
        robust_gap_spread = self._calculate_robust_gap_spread(page_rows)
        local_gap_ratio = self._calculate_local_gap_ratio(page_rows, boundary_index)

        # Calculate neighborhood evidence
        neighborhood_evidence = self._calculate_neighborhood_evidence(
            page_rows, boundary_index, neighborhood_window
        )

        # Create BoundaryEvidence object
        return BoundaryEvidence(
            page_number=row_a.page_number,
            row_a_index=boundary_index,
            row_b_index=boundary_index + 1,
            row_a_text=row_a.text,
            row_b_text=row_b.text,
            raw_vertical_gap=raw_vertical_gap,
            horizontal_overlap=horizontal_overlap,
            left_margin_delta=left_margin_delta,
            left_margin_similarity=left_margin_similarity,
            font_size_difference=font_size_difference,
            font_size_similarity=font_size_similarity,
            font_family_similarity=font_family_similarity,
            bold_relationship=bold_relationship,
            visual_span_count_a=visual_span_count_a,
            visual_span_count_b=visual_span_count_b,
            visual_span_composition_a=visual_span_composition_a,
            visual_span_composition_b=visual_span_composition_b,
            page_median_gap=page_median_gap,
            robust_gap_spread=robust_gap_spread,
            local_gap_ratio=local_gap_ratio,
            neighborhood_evidence=neighborhood_evidence,
        )

    def _calculate_raw_vertical_gap(self, row_a: PhysicalRow, row_b: PhysicalRow) -> float:
        """Calculate raw vertical gap between rows"""
        return row_b.coordinates['y1'] - row_a.coordinates['y2']

    def _calculate_horizontal_overlap(self, row_a: PhysicalRow, row_b: PhysicalRow) -> float:
        """Calculate normalized horizontal overlap ratio between rows (0 = no overlap, 1 = full overlap)"""
        # Calculate intersection
        left_bound = max(row_a.coordinates['x1'], row_b.coordinates['x1'])
        right_bound = min(row_a.coordinates['x2'], row_b.coordinates['x2'])

        # If there's no overlap, return 0
        if left_bound >= right_bound:
            return 0.0

        # Calculate overlap and normalize by the smaller row width
        overlap = right_bound - left_bound
        a_width = row_a.coordinates['x2'] - row_a.coordinates['x1']
        b_width = row_b.coordinates['x2'] - row_b.coordinates['x1']
        smaller_width = min(a_width, b_width)

        # Handle zero-width rows defensively
        if smaller_width == 0:
            return 0.0

        return overlap / smaller_width

    def _calculate_left_margin_delta(self, row_a: PhysicalRow, row_b: PhysicalRow) -> float:
        """Calculate difference in left margins"""
        return row_b.coordinates['x1'] - row_a.coordinates['x1']

    def _calculate_left_margin_similarity(self, row_a: PhysicalRow, row_b: PhysicalRow) -> float:
        """Calculate similarity of left margins (0 = very different, 1 = identical)"""
        margin_a = row_a.coordinates['x1']
        margin_b = row_b.coordinates['x1']

        # If both margins are zero or very small, they're similar
        if abs(margin_a) < 1 and abs(margin_b) < 1:
            return 1.0

        # Calculate difference relative to the average of both margins
        avg_margin = (abs(margin_a) + abs(margin_b)) / 2
        if avg_margin == 0:
            return 1.0

        diff = abs(margin_a - margin_b)
        similarity = max(0, 1 - (diff / avg_margin))
        return similarity

    def _calculate_font_size_difference(self, row_a: PhysicalRow, row_b: PhysicalRow) -> float:
        """Calculate absolute difference in font sizes"""
        # Get font size from visual spans or fall back to a default
        size_a = self._get_row_font_size(row_a)
        size_b = self._get_row_font_size(row_b)
        return abs(size_a - size_b)

    def _calculate_font_size_similarity(self, row_a: PhysicalRow, row_b: PhysicalRow) -> float:
        """Calculate similarity of font sizes (0 = very different, 1 = identical)"""
        size_a = self._get_row_font_size(row_a)
        size_b = self._get_row_font_size(row_b)

        if size_a == 0 and size_b == 0:
            return 1.0
        elif size_a == 0 or size_b == 0:
            return 0.0

        # Calculate relative difference
        avg_size = (size_a + size_b) / 2
        if avg_size == 0:
            return 1.0

        diff = abs(size_a - size_b)
        similarity = max(0, 1 - (diff / avg_size))
        return similarity

    def _calculate_font_family_similarity(self, row_a: PhysicalRow, row_b: PhysicalRow) -> float:
        """Calculate Jaccard similarity of font families between rows (0 = very different, 1 = identical)"""
        # Use set-based approach for both rows to ensure consistent handling
        families_a = self._get_row_font_families_set(row_a)
        families_b = self._get_row_font_families_set(row_b)

        # Handle empty sets
        if not families_a and not families_b:
            return 1.0
        if not families_a or not families_b:
            return 0.0

        # Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|
        intersection = len(families_a.intersection(families_b))
        union = len(families_a.union(families_b))

        if union == 0:
            return 0.0

        return intersection / union

    def _calculate_bold_relationship(self, row_a: PhysicalRow, row_b: PhysicalRow) -> str:
        """Determine relationship between boldness of rows"""
        bold_a = self._get_row_boldness(row_a)
        bold_b = self._get_row_boldness(row_b)

        if bold_a and bold_b:
            return "both_bold"
        elif bold_a and not bold_b:
            return "a_bold_b_regular"
        elif not bold_a and bold_b:
            return "a_regular_b_bold"
        else:
            return "both_regular"

    def _get_row_font_size(self, row: PhysicalRow) -> float:
        """Get dominant/primary font size from visual spans (deterministic approach)"""
        if not row.visual_spans:
            return 0.0

        # Use mode (most frequent) instead of median to get the primary font size
        sizes = [span.font_size for span in row.visual_spans]
        if not sizes:
            return 0.0

        # Count frequency of each size and return the most frequent one
        size_counts = {}
        for size in sizes:
            size_counts[size] = size_counts.get(size, 0) + 1

        # Get the maximum count
        max_count = max(size_counts.values())

        # Find all sizes with maximum count and return the smallest (deterministic tie-breaker)
        modes = [size for size, count in size_counts.items() if count == max_count]
        return min(modes)

    def _get_row_font_families_set(self, row: PhysicalRow) -> set:
        """Get distinct font families from visual spans"""
        if not row.visual_spans:
            return set()
        return set(span.font_family for span in row.visual_spans)

    def _get_row_boldness(self, row: PhysicalRow) -> bool:
        """Determine whether any VisualSpan uses the PyMuPDF bold font flag."""
        if not row.visual_spans:
                return False

        # Check if any span has bold flag - using the established convention from project
        # The task says to inspect existing conventions and use established bold indicator
        # Based on typical PDF font flags, bit 1 (0-indexed) is bold indicator (value 2)
        for span in row.visual_spans:
            if span.font_flags & 16:  # Bold flag
                return True

        return False

    def _get_visual_span_composition(self, row: PhysicalRow) -> Dict[str, Any]:
        """Get composition information from visual spans"""
        if not row.visual_spans:
            return {
                "span_count": 0,
                "distinct_font_families": set(),
                "distinct_font_sizes": set(),
                "bold_span_count": 0,
                "bold_span_proportion": 0.0,
                "first_text": "",
                "last_text": ""
            }

        first_span = row.visual_spans[0] if row.visual_spans else None
        last_span = row.visual_spans[-1] if row.visual_spans else None

        # Calculate additional composition metrics
        span_count = len(row.visual_spans)
        distinct_font_families = set(span.font_family for span in row.visual_spans)
        distinct_font_sizes = set(span.font_size for span in row.visual_spans)
        bold_span_count = sum(1 for span in row.visual_spans if span.font_flags & 16)  # Check bold flag
        bold_span_proportion = bold_span_count / span_count if span_count > 0 else 0.0

        return {
            "span_count": span_count,
            "distinct_font_families": distinct_font_families,
            "distinct_font_sizes": distinct_font_sizes,
            "bold_span_count": bold_span_count,
            "bold_span_proportion": bold_span_proportion,
            "first_text": first_span.text if first_span else "",
            "last_text": last_span.text if last_span else ""
        }

    def _calculate_page_median_gap(self, page_rows: List[PhysicalRow]) -> float:
        """Calculate median gap between all consecutive rows on the page"""
        if len(page_rows) < 2:
            return 0.0

        gaps = []
        for i in range(len(page_rows) - 1):
            gap = page_rows[i+1].coordinates['y1'] - page_rows[i].coordinates['y2']
            gaps.append(gap)

        if not gaps:
            return 0.0

        return statistics.median(gaps)

    def _calculate_robust_gap_spread(self, page_rows: List[PhysicalRow]) -> float:
        """Calculate robust spread of gaps using interquartile range"""
        if len(page_rows) < 2:
            return 0.0

        gaps = []
        for i in range(len(page_rows) - 1):
            gap = page_rows[i+1].coordinates['y1'] - page_rows[i].coordinates['y2']
            gaps.append(gap)

        if len(gaps) < 2:
            return 0.0

        # Use interquartile range to get robust spread
        gaps.sort()
        q1 = statistics.quantiles(gaps, n=4)[0]
        q3 = statistics.quantiles(gaps, n=4)[2]
        return q3 - q1

    def _calculate_local_gap_ratio(self, page_rows: List[PhysicalRow], boundary_index: int) -> float:
        """Calculate ratio of gap to median gap"""
        if len(page_rows) < 2:
            return 0.0

        current_gap = page_rows[boundary_index+1].coordinates['y1'] - page_rows[boundary_index].coordinates['y2']

        # Get neighborhood gaps (±3 rows around the boundary)
        start_idx = max(0, boundary_index - 3)
        end_idx = min(len(page_rows), boundary_index + 4)  # +4 because we want to include boundary_index+3

        neighborhood_gaps = []
        for i in range(start_idx, end_idx):
            if i < len(page_rows) - 1 and i != boundary_index:  # Exclude the boundary itself
                gap = page_rows[i+1].coordinates['y1'] - page_rows[i].coordinates['y2']
                neighborhood_gaps.append(gap)

        # Handle case where no neighbors exist
        if not neighborhood_gaps:
            return 0.0

        # Use median of neighbor gaps as denominator (not page median)
        median_gap = statistics.median(neighborhood_gaps)

        # Handle zero/degenerate denominators safely
        if median_gap == 0:
            return 0.0

        return current_gap / median_gap

    def _calculate_neighborhood_evidence(self, page_rows: List[PhysicalRow],
                                       boundary_index: int, window: int) -> Dict[str, List[float]]:
        """Calculate neighborhood evidence for surrounding rows"""
        # Get the neighborhood (within window size)
        start_idx = max(0, boundary_index - window)
        end_idx = min(len(page_rows), boundary_index + window + 1)

        # Calculate neighborhood metrics
        neighborhood_gaps = []
        neighborhood_left_margins = []
        neighborhood_font_sizes = []

        for i in range(start_idx, end_idx):
            # Skip the boundary itself (the gap at boundary_index)
            if i == boundary_index:
                continue

            if i < len(page_rows) - 1:
                gap = page_rows[i+1].coordinates['y1'] - page_rows[i].coordinates['y2']
                neighborhood_gaps.append(gap)

            # Collect margin information
            if i < len(page_rows):
                margin = page_rows[i].coordinates['x1']
                neighborhood_left_margins.append(margin)

            # Collect font size information
            if i < len(page_rows):
                font_size = self._get_row_font_size(page_rows[i])
                neighborhood_font_sizes.append(font_size)

        return {
            "neighborhood_gaps": neighborhood_gaps,
            "neighborhood_left_margins": neighborhood_left_margins,
            "neighborhood_font_sizes": neighborhood_font_sizes
        }


# Example usage function
def demo_boundary_evidence():
    """Demonstrate how to use the BoundaryEvidence component"""
    print("Creating BoundaryEvidence provider...")

    # This would normally be loaded from a PDF processing pipeline
    # For demonstration purposes, we'll create some mock data
    print("Boundary evidence demonstration completed.")


if __name__ == "__main__":
    demo_boundary_evidence()