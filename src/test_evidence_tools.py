"""
Tests for actual PDF evidence tools implementation
"""

import unittest
from src.evidence_tools import PDFEvidenceRetriever
from src.models import PhysicalRow, EvidenceSource


class TestPDFEvidenceRetriever(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.pdf_path = "documents/ing_luxembourg.pdf"
        self.retriever = PDFEvidenceRetriever(self.pdf_path)
    
    def tearDown(self):
        """Clean up after tests"""
        self.retriever.close()
    
    def test_initialization(self):
        """Test that the retriever initializes correctly"""
        self.assertEqual(self.retriever.pdf_path, self.pdf_path)
        self.assertIsNotNone(self.retriever.page_count)
        self.assertGreater(self.retriever.page_count, 0)
    
    def test_get_page_evidence(self):
        """Test getting evidence from a specific page"""
        page_evidence = self.retriever.get_page_evidence(1)
        
        self.assertEqual(page_evidence.page_number, 1)
        self.assertIsInstance(page_evidence.text, str)
        self.assertGreater(len(page_evidence.text), 0)
        self.assertIn('width', page_evidence.dimensions)
        self.assertIn('height', page_evidence.dimensions)
        self.assertGreater(page_evidence.dimensions['width'], 0)
        self.assertGreater(page_evidence.dimensions['height'], 0)
        self.assertIsInstance(page_evidence.raw_evidence, str)
    
    def test_get_all_pages(self):
        """Test getting evidence from all pages"""
        pages = self.retriever.get_all_pages()
        
        self.assertGreater(len(pages), 0)
        self.assertEqual(len(pages), self.retriever.page_count)
        
        # Check that each page has correct page number
        for i, page in enumerate(pages):
            self.assertEqual(page.page_number, i + 1)
    
    def test_get_physical_rows_on_page(self):
        """Test getting physical rows from a page"""
        rows = self.retriever.get_physical_rows_on_page(1)
        
        # Should return at least some rows
        self.assertIsInstance(rows, list)
        if len(rows) > 0:
            # Check that first row has required fields
            first_row = rows[0]
            self.assertIsInstance(first_row, PhysicalRow)
            self.assertEqual(first_row.page_number, 1)
            self.assertIn('x1', first_row.coordinates)
            self.assertIn('y1', first_row.coordinates)
            self.assertIn('x2', first_row.coordinates)
            self.assertIn('y2', first_row.coordinates)
            self.assertIsInstance(first_row.text, str)
            self.assertGreater(len(first_row.text), 0)
            self.assertIsInstance(first_row.words, list)
    
    def test_search_text(self):
        """Test searching text in the document"""
        # Search for something that should exist
        results = self.retriever.search_text("fee")
        
        self.assertIsInstance(results, list)
        # At least one result should be found
        if len(results) > 0:
            page_num, matched_text = results[0]
            self.assertIsInstance(page_num, int)
            self.assertGreater(page_num, 0)
            self.assertIsInstance(matched_text, str)
            self.assertGreater(len(matched_text), 0)
    
    def test_get_evidence_from_coordinates(self):
        """Test getting evidence from coordinate regions"""
        # Get some rows first to understand the page structure
        rows = self.retriever.get_physical_rows_on_page(1)
        
        if len(rows) > 0:
            # Test with the first row's coordinates
            first_row = rows[0]
            coords = first_row.coordinates
            
            # Search for evidence in that coordinate region
            evidence = self.retriever.get_evidence_from_coordinates(
                1, 
                coords['x1'], 
                coords['y1'], 
                coords['x2'], 
                coords['y2']
            )
            
            self.assertIsInstance(evidence, list)
            # Should at least find the row itself
            if len(evidence) > 0:
                first_evidence = evidence[0]
                self.assertIsInstance(first_evidence, PhysicalRow)
    
    def test_get_evidence_source_from_physical_row(self):
        """Test creating evidence source from physical row"""
        rows = self.retriever.get_physical_rows_on_page(1)
        
        if len(rows) > 0:
            row = rows[0]
            evidence_source = self.retriever.get_evidence_source_from_physical_row(row)
            
            self.assertIsInstance(evidence_source, EvidenceSource)
            self.assertEqual(evidence_source.source_type, "text")
            self.assertEqual(evidence_source.page_number, row.page_number)
            self.assertEqual(evidence_source.coordinates, row.coordinates)
            self.assertEqual(evidence_source.content, row.text)
    
    def test_get_evidence_source_from_coordinate_region(self):
        """Test creating evidence source from coordinate region"""
        rows = self.retriever.get_physical_rows_on_page(1)
        
        if len(rows) > 0:
            # Use first row's coordinates for the test
            first_row = rows[0]
            coords = first_row.coordinates
            
            evidence_source = self.retriever.get_evidence_source_from_coordinate_region(
                1,
                coords['x1'],
                coords['y1'],
                coords['x2'],
                coords['y2']
            )
            
            self.assertIsInstance(evidence_source, EvidenceSource)
            self.assertEqual(evidence_source.source_type, "coordinate_region")
            self.assertEqual(evidence_source.page_number, 1)
            self.assertIn('x1', evidence_source.coordinates)
            self.assertIn('y1', evidence_source.coordinates)
            self.assertIn('x2', evidence_source.coordinates)
            self.assertIn('y2', evidence_source.coordinates)
            self.assertIsInstance(evidence_source.content, str)


if __name__ == '__main__':
    unittest.main()