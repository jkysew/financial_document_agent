"""
Evidence manager for Financial Document Agent v3
Handles physical evidence extraction and management
"""

from typing import List, Dict, Any
from src.models import PhysicalRow, EvidenceSource


class EvidenceManager:
    """Manages physical evidence extraction and organization"""
    
    def __init__(self):
        self.physical_rows: List[PhysicalRow] = []
        self.evidence_sources: List[EvidenceSource] = []
    
    def add_physical_row(self, page_number: int, coordinates: Dict[str, float], 
                        text: str, words: List[Dict[str, Any]],
                        row_id: str = None):
        """Add a physical row to the evidence"""
        row = PhysicalRow(
            page_number=page_number,
            coordinates=coordinates,
            text=text,
            words=words,
            row_id=row_id
        )
        self.physical_rows.append(row)
    
    def add_evidence_source(self, source_type: str, page_number: int, 
                           coordinates: Dict[str, float], content: str, context: str):
        """Add an evidence source"""
        evidence = EvidenceSource(
            source_type=source_type,
            page_number=page_number,
            coordinates=coordinates,
            content=content,
            context=context
        )
        self.evidence_sources.append(evidence)
    
    def get_rows_for_page(self, page_number: int) -> List[PhysicalRow]:
        """Get all physical rows for a specific page"""
        return [row for row in self.physical_rows if row.page_number == page_number]
    
    def get_all_evidence(self) -> Dict[str, Any]:
        """Get all evidence data"""
        return {
            "physical_rows": self.physical_rows,
            "evidence_sources": self.evidence_sources
        }