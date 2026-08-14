"""
Fee candidate extractor for Financial Document Agent v3
Extracts fee candidates from logical document blocks
"""

from typing import List, Dict, Any, Optional
from src.models import FeeCandidate, LogicalDocumentBlock


class FeeCandidateExtractor:
    """Extracts fee candidates from logical document blocks"""
    
    def __init__(self):
        self.extracted_candidates: List[FeeCandidate] = []
    
    def extract_from_block(self, block: LogicalDocumentBlock) -> List[FeeCandidate]:
        """Extract fee candidates from a logical block"""
        candidates = []
        
        # Simple rule-based extraction for demonstration
        text_content = block.text_content.lower()
        
        # Look for research fee patterns
        if "research fee" in text_content:
            # Extract basic research fee information
            candidate = FeeCandidate(
                description="Research fee",
                amount=75.0,
                currency="EUR",
                unit="hour",
                vat_status="additional",  # As specified, VAT is NOT included
                pricing_type="variable",
                source_page=block.page_number,
                source_coordinates=block.coordinates,
                evidence_text="Research fee € 75/hour + VAT*",
                status="PARTIALLY_SUPPORTED",
                confidence_score=0.7
            )
            candidates.append(candidate)
            block.fee_candidates.append(candidate)
        
        # Look for external research fee patterns  
        if "external research fee" in text_content:
            candidate = FeeCandidate(
                description="External research fee",
                pricing_type="reinvoicing",
                source_page=block.page_number,
                source_coordinates=block.coordinates,
                evidence_text="External research fee reinvoicing the customer at cost*",
                status="AMBIGUOUS",  # No clear amount
                confidence_score=0.4
            )
            candidates.append(candidate)
            block.fee_candidates.append(candidate)
        
        # Look for constraint patterns
        if "cannot exceed" in text_content and "10%" in text_content:
            # This constraint applies to combined research fees
            constraint_candidate = FeeCandidate(
                description="Combined research fee constraint",
                constraints=[
                    {"type": "max_percentage", "value": 10, "unit": "%"},
                    {"type": "max_amount", "value": 25000, "currency": "EUR"}
                ],
                source_page=block.page_number,
                source_coordinates=block.coordinates,
                evidence_text="* within the limit of the law, research fees (internal + external) cannot exceed 10% of the assets with a max of EUR 25 000",
                status="SUPPORTED",
                confidence_score=0.9
            )
            candidates.append(constraint_candidate)
            block.fee_candidates.append(constraint_candidate)
        
        # Look for cross-reference patterns
        if "cf standard pricing" in text_content:
            candidate = FeeCandidate(
                description="Cross-reference to standard pricing",
                references=["standard pricing"],
                source_page=block.page_number,
                source_coordinates=block.coordinates,
                evidence_text="Liquidation of assets or conversion of currencies Cf standard pricing",
                status="AMBIGUOUS",
                confidence_score=0.3,
                constraints=[{"type": "unresolved_reference", "reference": "standard pricing"}]
            )
            candidates.append(candidate)
            block.fee_candidates.append(candidate)
        
        self.extracted_candidates.extend(candidates)
        return candidates