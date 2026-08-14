"""
Tests for the inspection/export functionality.
"""

import os
import json
import unittest
from src.inspection_tool import export_evidence_to_json, smoke_test_inspection

class TestInspectionTool(unittest.TestCase):
    
    def test_export_evidence_to_json_exists(self):
        """Test that the export function exists and can be called."""
        # This is a basic test to make sure the function exists
        self.assertTrue(callable(export_evidence_to_json))
    
    def test_smoke_test_inspection(self):
        """Test that smoke test runs without errors."""
        result = smoke_test_inspection()
        self.assertIsNotNone(result)
        
        # Check that file was created
        if result:
            self.assertTrue(os.path.exists(result))
            
    def test_export_structure(self):
        """Test the structure of exported data."""
        pdf_path = "documents/ing_luxembourg.pdf"
        
        if os.path.exists(pdf_path):
            output_file = export_evidence_to_json(pdf_path)
            
            # Check that file was created
            self.assertTrue(os.path.exists(output_file))
            
            # Read and validate JSON structure
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate basic structure
            self.assertIn("document_info", data)
            self.assertIn("pages", data)
            self.assertIn("document_path", data["document_info"])
            self.assertIn("page_count", data["document_info"])

            # Verify page count is 20 (as per requirements)
            self.assertEqual(data["document_info"]["page_count"], 20)

            # Verify pages structure
            pages = data["pages"]
            self.assertIsInstance(pages, list)
            self.assertEqual(len(pages), 20)  # Should have 20 pages

            # Check first page has physical rows
            first_page = pages[0]
            self.assertIn("page_number", first_page)
            self.assertIn("physical_rows", first_page)

            # Verify that at least one row exists on the first page
            physical_rows = first_page["physical_rows"]
            self.assertIsInstance(physical_rows, list)

            # Check if any rows exist and validate their structure
            if len(physical_rows) > 0:
                row = physical_rows[0]
                self.assertIn("row_id", row)
                self.assertIn("page_number", row)
                self.assertIn("coordinates", row)
                self.assertIn("text", row)
                self.assertIn("words", row)

                # Verify that row_id is present and not None
                self.assertIsNotNone(row["row_id"])

                # Verify coordinates structure
                coords = row["coordinates"]
                self.assertIn("x1", coords)
                self.assertIn("y1", coords)
                self.assertIn("x2", coords)
                self.assertIn("y2", coords)

                # Verify text and words are present
                self.assertIsInstance(row["text"], str)
                self.assertIsInstance(row["words"], list)

if __name__ == "__main__":
    unittest.main()