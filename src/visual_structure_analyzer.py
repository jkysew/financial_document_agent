"""
Visual Structure Analyzer for Financial Document Agent v3
Analyzes physical document layout to determine logical block boundaries
using only available physical signals: coordinates, text content, and row structure.
"""

from typing import List, Dict, Tuple
from src.models import PhysicalRow


class VisualStructureAnalyzer:
    """Analyzes physical document layout to determine logical block boundaries"""
    
    def __init__(self):
        self.document_stats = {}
    
    def _calculate_row_spacing(self, rows: List[PhysicalRow]) -> List[float]:
        """Calculate vertical spacing between consecutive rows"""
        if len(rows) < 2:
            return []
        
        spacings = []
        for i in range(1, len(rows)):
            prev_row = rows[i-1]
            curr_row = rows[i]
            
            # Calculate vertical distance from bottom of previous row to top of current
            prev_bottom = prev_row.coordinates['y2']
            curr_top = curr_row.coordinates['y1']
            spacing = curr_top - prev_bottom
            
            spacings.append(spacing)
        
        return spacings
    
    def _calculate_document_statistics(self, rows: List[PhysicalRow]) -> Dict[str, float]:
        """Calculate document-wide statistics for spacing and alignment"""
        if not rows:
            return {}
        
        # Calculate spacing statistics
        spacings = self._calculate_row_spacing(rows)
        
        # Calculate row dimensions
        heights = [row.coordinates['y2'] - row.coordinates['y1'] for row in rows]
        
        # Calculate horizontal alignment reference points
        x1_coords = [row.coordinates['x1'] for row in rows]
        x2_coords = [row.coordinates['x2'] for row in rows]
        
        stats = {
            'avg_spacing': sum(spacings) / len(spacings) if spacings else 0,
            'spacing_std': self._calculate_std_deviation(spacings),
            'avg_height': sum(heights) / len(heights) if heights else 0,
            'height_std': self._calculate_std_deviation(heights),
            'min_x1': min(x1_coords) if x1_coords else 0,
            'max_x2': max(x2_coords) if x2_coords else 0
        }
        
        return stats
    
    def _calculate_std_deviation(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values"""
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _is_same_block(self, prev_row: PhysicalRow, curr_row: PhysicalRow, 
                      stats: Dict[str, float]) -> bool:
        """Determine if two consecutive rows should belong to the same logical block"""
        
        # If no statistics available, default to same block
        if not stats:
            return True
        
        # Calculate vertical spacing
        prev_bottom = prev_row.coordinates['y2']
        curr_top = curr_row.coordinates['y1']
        spacing = curr_top - prev_bottom
        
        # Calculate horizontal alignment difference
        x1_diff = abs(curr_row.coordinates['x1'] - prev_row.coordinates['x1'])
        x2_diff = abs(curr_row.coordinates['x2'] - prev_row.coordinates['x2'])
        
        # Calculate height difference
        prev_height = prev_row.coordinates['y2'] - prev_row.coordinates['y1']
        curr_height = curr_row.coordinates['y2'] - curr_row.coordinates['y1']
        height_diff = abs(curr_height - prev_height)
        
        # Determine if spacing is normal (within statistical range)
        normal_spacing = abs(spacing - stats['avg_spacing']) <= stats['spacing_std']
        
        # Determine if horizontal alignment is consistent
        aligned_x1 = x1_diff <= 20  # Small difference in left alignment
        aligned_x2 = x2_diff <= 20  # Small difference in right alignment
        
        # Determine if height variation is normal
        normal_height = height_diff <= stats['height_std'] * 2  # Allow some variation
        
        # Rows belong to same block if:
        # 1. Spacing is normal AND
        # 2. Horizontal alignment is consistent AND  
        # 3. Height variation is acceptable
        return (normal_spacing and aligned_x1 and aligned_x2 and normal_height)
    
    def analyze_block_boundaries(self, rows: List[PhysicalRow]) -> List[Tuple[int, int]]:
        """
        Analyze physical rows to determine logical block boundaries.
        Returns list of (start_index, end_index) tuples for each block.
        """
        if not rows:
            return []
        
        # Calculate document statistics
        stats = self._calculate_document_statistics(rows)
        
        # Group consecutive rows into blocks
        blocks = []
        current_start = 0
        current_end = 0
        
        for i in range(1, len(rows)):
            prev_row = rows[i-1]
            curr_row = rows[i]
            
            # Check if this row should continue the current block
            if self._is_same_block(prev_row, curr_row, stats):
                current_end = i
            else:
                # Start a new block
                blocks.append((current_start, current_end))
                current_start = i
                current_end = i
        
        # Add the final block
        blocks.append((current_start, current_end))
        
        return blocks
    
    def group_rows_into_blocks(self, rows: List[PhysicalRow]) -> List[List[PhysicalRow]]:
        """
        Group physical rows into logical blocks based on visual structure analysis.
        Returns list of lists, where each inner list contains rows belonging to same block.
        """
        if not rows:
            return []
        
        # Get block boundaries
        boundaries = self.analyze_block_boundaries(rows)
        
        # Create grouped rows
        grouped_blocks = []
        for start_idx, end_idx in boundaries:
            block_rows = rows[start_idx:end_idx+1]
            grouped_blocks.append(block_rows)
        
        return grouped_blocks


# Example usage function (for testing)
def demo_visual_analysis():
    """Demonstrate the visual structure analysis"""
    # This would be called from document processor
    pass