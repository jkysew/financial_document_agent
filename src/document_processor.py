"""
Main document processor for Financial Document Agent v3
"""

from typing import List, Dict, Any
from src.models import LogicalDocumentBlock, PhysicalRow
from src.evidence_manager import EvidenceManager
from src.logical_block_generator import LogicalBlockGenerator
from src.fee_candidate_extractor import FeeCandidateExtractor
from src.validator import Validator


class DocumentProcessor:
    """Main processor that orchestrates the v3 pipeline"""
    
    def __init__(self):
        self.evidence_manager = EvidenceManager()
        self.block_generator = LogicalBlockGenerator()
        self.extractor = FeeCandidateExtractor()
        self.validator = Validator()
    
    def process_document(self, physical_rows: List[PhysicalRow]) -> Dict[str, Any]:
        """Process a document through the v3 pipeline"""
        
        # Step 1: Store physical evidence
        for row in physical_rows:
            self.evidence_manager.add_physical_row(
                page_number=row.page_number,
                coordinates=row.coordinates,
                text=row.text,
                words=row.words,
                row_id=row.row_id
            )
        
        # Step 2: Create logical blocks using deterministic grouping from physical rows
        self.block_generator.create_blocks_from_rows(self.evidence_manager.physical_rows)
        # Step 3: Extract fee candidates
        self._extract_fee_candidates()
        
        # Step 4: Validate results
        all_blocks = self.block_generator.get_all_blocks()
        validated_blocks = self.validator.validate_all_blocks(all_blocks)
        
        # Step 5: Format output
        result = self._format_output(validated_blocks)
        
        return result
    
    def _create_logical_blocks(self):
        """Create logical blocks from physical evidence (simplified for demo)"""
        # For demonstration, we'll create one logical block per page
        pages = set(row.page_number for row in self.evidence_manager.physical_rows)
        
        for page in pages:
            page_rows = self.evidence_manager.get_rows_for_page(page)
            
            # Simple coordinate calculation for the block
            if page_rows:
                x_coords = [row.coordinates['x1'] for row in page_rows] + [row.coordinates['x2'] for row in page_rows]
                y_coords = [row.coordinates['y1'] for row in page_rows] + [row.coordinates['y2'] for row in page_rows]
                
                coordinates = {
                    'x1': min(x_coords),
                    'y1': min(y_coords),
                    'x2': max(x_coords),
                    'y2': max(y_coords)
                }
                
                # Combine text content from all rows
                text_content = " ".join(row.text for row in page_rows)
                
                self.block_generator.create_logical_block(
                    page_number=page,
                    coordinates=coordinates,
                    text_content=text_content,
                    physical_rows=page_rows
                )
    
    def _extract_fee_candidates(self):
        """Extract fee candidates from all logical blocks"""
        blocks = self.block_generator.get_all_blocks()
        for block in blocks:
            self.extractor.extract_from_block(block)
    
    def _format_output(self, blocks: List[LogicalDocumentBlock]) -> Dict[str, Any]:
        """Format the final output"""
        formatted_blocks = []
        
        for block in blocks:
            # Convert PhysicalRow objects to dictionary format for JSON serialization
            physical_rows_data = []
            for row in block.physical_rows:
                physical_rows_data.append({
                    'page_number': row.page_number,
                    'coordinates': row.coordinates,
                    'text': row.text,
                    'words': row.words,
                    'row_id': row.row_id
                })
            
            formatted_block = {
                'block_id': block.block_id,
                'type': block.type,
                'page_number': block.page_number,
                'coordinates': block.coordinates,
                'text_content': block.text_content,
                'status': block.status.value,
                'confidence_score': block.confidence_score,
                'physical_rows': physical_rows_data,
                'fee_candidates': []
            }
            
            for candidate in block.fee_candidates:
                formatted_candidate = {
                    'description': candidate.description,
                    'amount': candidate.amount,
                    'currency': candidate.currency,
                    'unit': candidate.unit,
                    'vat_status': candidate.vat_status,
                    'pricing_type': candidate.pricing_type,
                    'references': candidate.references,
                    'constraints': candidate.constraints,
                    'source_page': candidate.source_page,
                    'source_coordinates': candidate.source_coordinates,
                    'evidence_text': candidate.evidence_text,
                    'status': candidate.status.value,
                    'confidence_score': candidate.confidence_score
                }
                formatted_block['fee_candidates'].append(formatted_candidate)
            
            formatted_blocks.append(formatted_block)
        
        return {
            'blocks': formatted_blocks,
            'summary': {
                'total_blocks': len(formatted_blocks),
                'total_candidates': sum(len(block['fee_candidates']) for block in formatted_blocks)
            }
        }