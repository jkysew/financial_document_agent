"""
Validator for Financial Document Agent v3
Validates fee candidates and assigns status
"""

from typing import List, Dict, Any
from src.models import FeeCandidate, LogicalDocumentBlock, Status


class Validator:
    """Validates fee candidates and assigns appropriate status"""
    
    def __init__(self):
        pass
    
    def validate_candidate(self, candidate: FeeCandidate) -> FeeCandidate:
        """Validate a single fee candidate and update its status"""
        # Basic validation rules
        if candidate.amount is not None and candidate.currency is not None:
            candidate.status = Status.SUPPORTED
            candidate.confidence_score = min(1.0, max(0.0, candidate.confidence_score + 0.2))
        elif candidate.amount is None and candidate.currency is None:
            # If no amount or currency, it's ambiguous
            if candidate.pricing_type == "reinvoicing" or candidate.pricing_type == "cost":
                candidate.status = Status.PARTIALLY_SUPPORTED
            else:
                candidate.status = Status.AMBIGUOUS
        else:
            # Partial information
            candidate.status = Status.PARTIALLY_SUPPORTED
            candidate.confidence_score = min(1.0, max(0.0, candidate.confidence_score + 0.1))
        
        return candidate
    
    def validate_block(self, block: LogicalDocumentBlock) -> LogicalDocumentBlock:
        """Validate all candidates in a logical block"""
        for candidate in block.fee_candidates:
            self.validate_candidate(candidate)
        
        # Set block status based on candidates
        supported_count = sum(1 for c in block.fee_candidates if c.status == Status.SUPPORTED)
        partial_count = sum(1 for c in block.fee_candidates if c.status == Status.PARTIALLY_SUPPORTED)
        ambiguous_count = sum(1 for c in block.fee_candidates if c.status == Status.AMBIGUOUS)
        
        if supported_count > 0:
            block.status = Status.SUPPORTED
        elif partial_count > 0:
            block.status = Status.PARTIALLY_SUPPORTED
        elif ambiguous_count > 0:
            block.status = Status.AMBIGUOUS
        else:
            block.status = Status.UNSUPPORTED
            
        return block
    
    def validate_all_blocks(self, blocks: List[LogicalDocumentBlock]) -> List[LogicalDocumentBlock]:
        """Validate all logical blocks"""
        for block in blocks:
            self.validate_block(block)
        return blocks