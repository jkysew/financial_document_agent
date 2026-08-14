"""
Test suite for Financial Document Agent v3 models
"""

import unittest
from src.models import PhysicalRow, EvidenceSource, FeeCandidate, LogicalDocumentBlock


class TestPhysicalRow(unittest.TestCase):
    
    def test_physical_row_creation(self):
        """Test PhysicalRow creation with required fields"""
        row = PhysicalRow(
            page_number=1,
            coordinates={"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 50.0},
            text="Test row content",
            words=[{"text": "test", "x": 10.0, "y": 10.0}]
        )
        
        self.assertEqual(row.page_number, 1)
        self.assertEqual(row.coordinates, {"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 50.0})
        self.assertEqual(row.text, "Test row content")
        self.assertEqual(row.words, [{"text": "test", "x": 10.0, "y": 10.0}])
        self.assertIsNotNone(row.row_id)  # Should be auto-generated


class TestEvidenceSource(unittest.TestCase):
    
    def test_evidence_source_creation(self):
        """Test EvidenceSource creation with required fields"""
        source = EvidenceSource(
            source_type="text",
            page_number=1,
            coordinates={"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 50.0},
            content="Test content",
            context="Test context"
        )
        
        self.assertEqual(source.source_type, "text")
        self.assertEqual(source.page_number, 1)
        self.assertEqual(source.coordinates, {"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 50.0})
        self.assertEqual(source.content, "Test content")
        self.assertEqual(source.context, "Test context")
        self.assertIsNotNone(source.evidence_id)  # Should be auto-generated


class TestFeeCandidate(unittest.TestCase):
    
    def test_fee_candidate_creation(self):
        """Test FeeCandidate creation with required fields"""
        candidate = FeeCandidate(
            description="Test fee",
        )
        
        self.assertEqual(candidate.description, "Test fee")
        self.assertIsNone(candidate.amount)
        self.assertEqual(candidate.vat_status, "unknown")
        self.assertEqual(candidate.pricing_type, "fixed")
        self.assertEqual(candidate.references, [])  # Should default to empty list
        self.assertEqual(candidate.constraints, [])  # Should default to empty list
        self.assertIsNotNone(candidate.candidate_id)  # Should be auto-generated


class TestLogicalDocumentBlock(unittest.TestCase):
    
    def test_logical_document_block_creation(self):
        """Test LogicalDocumentBlock creation with required fields"""
        block = LogicalDocumentBlock(
            block_id="test-block",
            type="fee_section",
            page_number=1,
            coordinates={"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 50.0},
            text_content="Test content",
            physical_rows=[],
            evidence_sources=[],
            fee_candidates=[]
        )
        
        self.assertEqual(block.block_id, "test-block")
        self.assertEqual(block.type, "fee_section")
        self.assertEqual(block.page_number, 1)
        self.assertEqual(block.coordinates, {"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 50.0})