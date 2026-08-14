"""
Output formatter for Financial Document Agent v3
Formats results into traceable, evidence-backed JSON
"""

import json
from typing import Dict, Any, List
from src.models import LogicalDocumentBlock, FeeCandidate


class OutputFormatter:
    """Formats final output into traceable JSON structure"""
    
    def __init__(self):
        pass
    
    def format_final_json(self, blocks: List[LogicalDocumentBlock]) -> str:
        """Format the final structured JSON output"""
        result = {
            "document_analysis": {
                "version": "v3",
                "generated_at": "2024-01-01T00:00:00Z",
                "logical_blocks": []
            }
        }
        
        for block in blocks:
            formatted_block = self._format_logical_block(block)
            result["document_analysis"]["logical_blocks"].append(formatted_block)
        
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    def _format_logical_block(self, block: LogicalDocumentBlock) -> Dict[str, Any]:
        """Format a single logical block"""
        formatted = {
            "block_id": block.block_id,
            "type": block.type,
            "page_number": block.page_number,
            "coordinates": block.coordinates,
            "text_content": block.text_content,
            "status": block.status.value,
            "confidence_score": block.confidence_score,
            "fee_candidates": [],
            "evidence_sources": []
        }
        
        # Format fee candidates
        for candidate in block.fee_candidates:
            formatted_candidate = self._format_fee_candidate(candidate)
            formatted["fee_candidates"].append(formatted_candidate)
        
        # Format evidence sources  
        for evidence in block.evidence_sources:
            formatted_evidence = {
                "source_type": evidence.source_type,
                "page_number": evidence.page_number,
                "coordinates": evidence.coordinates,
                "content": evidence.content,
                "context": evidence.context
            }
            formatted["evidence_sources"].append(formatted_evidence)
        
        return formatted
    
    def _format_fee_candidate(self, candidate: FeeCandidate) -> Dict[str, Any]:
        """Format a single fee candidate"""
        formatted = {
            "description": candidate.description,
            "amount": candidate.amount,
            "currency": candidate.currency,
            "unit": candidate.unit,
            "vat_status": candidate.vat_status,
            "pricing_type": candidate.pricing_type,
            "references": candidate.references,
            "constraints": candidate.constraints,
            "source_page": candidate.source_page,
            "source_coordinates": candidate.source_coordinates,
            "evidence_text": candidate.evidence_text,
            "status": candidate.status.value,
            "confidence_score": candidate.confidence_score
        }
        
        # Remove None values for cleaner output
        return {k: v for k, v in formatted.items() if v is not None}