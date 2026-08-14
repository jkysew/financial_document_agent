"""
Logical block generator for Financial Document Agent v3
Creates logical document blocks from physical evidence using deterministic grouping
"""

from typing import List, Dict, Any
from src.models import LogicalDocumentBlock, PhysicalRow, EvidenceSource
from src.models import Status


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
    
    def _group_rows_into_blocks(self, sorted_rows: List[PhysicalRow], 
                               vertical_spacing_threshold: int = 30) -> List[List[PhysicalRow]]:
        """Group physical rows into logical blocks based on vertical spacing"""
        if not sorted_rows:
            return []
        
        blocks = []
        current_block = [sorted_rows[0]]
        
        for i in range(1, len(sorted_rows)):
            prev_row = sorted_rows[i-1]
            curr_row = sorted_rows[i]
            
            # Calculate vertical distance between rows
            prev_bottom = prev_row.coordinates['y2']
            curr_top = curr_row.coordinates['y1']
            vertical_distance = curr_top - prev_bottom
            
            # If the vertical distance is small, they belong to the same block
            if vertical_distance <= vertical_spacing_threshold:
                current_block.append(curr_row)
            else:
                # Start a new block
                blocks.append(current_block)
                current_block = [curr_row]
        
        # Add the last block
        if current_block:
            blocks.append(current_block)
        
        return blocks
