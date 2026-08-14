"""
Integration test for DocumentProcessor using real evidence data
Tests that the new deterministic grouping works correctly
"""

import json
import unittest
from src.document_processor import DocumentProcessor
from src.models import PhysicalRow

class TestLogicalBlockIntegration(unittest.TestCase):
    """Test the integration of deterministic LogicalBlockGenerator with DocumentProcessor"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.processor = DocumentProcessor()
        
    def test_document_processor_integration_with_real_evidence(self):
        """Test DocumentProcessor with actual evidence from JSON file"""
        
        # Load the real evidence data
        try:
            with open('data/evidence/ing_luxembourg_evidence_output.json', 'r', encoding='utf-8') as f:
                evidence_data = json.load(f)
        except FileNotFoundError:
            self.fail("Error: Evidence file not found")
        except json.JSONDecodeError:
            self.fail("Error: Invalid JSON in evidence file")
        
        # Convert evidence data to PhysicalRow objects
        physical_rows = []
        row_display_ids = {}  # Maps row_id to display reference (P02-R001 format)
        page_row_counts = {}  # Tracks row count per page for display IDs

        # Handle the actual JSON structure: pages -> physical_rows
        if isinstance(evidence_data, dict) and 'pages' in evidence_data:
            pages = evidence_data['pages']
            for page in pages:
                if 'physical_rows' in page:
                    # Initialize row counter for this page
                    page_number = page.get('page_number', 1)
                    page_row_counts[page_number] = 0
                    
                    for row_data in page['physical_rows']:
                        physical_row = PhysicalRow(
                            page_number=row_data['page_number'],
                            coordinates=row_data['coordinates'],
                            text=row_data['text'],
                            words=row_data['words'],
                            row_id=row_data['row_id']
                        )
                        # Preserve the existing UUID row_id from evidence data if available
                        if 'row_id' in row_data:
                            physical_row.row_id = row_data['row_id']
                        
                        physical_rows.append(physical_row)
                        
                        # Assign display ID based on page and position
                        page_row_counts[page_number] += 1
                        display_id = f"P{page_number:02d}-R{page_row_counts[page_number]:03d}"
                        row_display_ids[physical_row.row_id] = display_id
                else:
                    # Skip pages without physical_rows
                    continue
        else:
            self.fail("Unexpected JSON structure: missing 'pages' key at root level")

        self.assertGreater(len(physical_rows), 0, "No valid physical rows loaded")
        print(f"Loaded {len(physical_rows)} physical rows")

        # Get page information
        pages = set(row.page_number for row in physical_rows)
        print(f"Data spans {len(pages)} pages: {sorted(pages)}")

        # Test the DocumentProcessor with real evidence
        try:
            result = self.processor.process_document(physical_rows)

            # Verify processing completed without exception
            self.assertIsNotNone(result, "Processing should return a result")
            self.assertIn('blocks', result, "Result should contain blocks")
            self.assertIsInstance(result['blocks'], list, "Blocks should be a list")
            if not result['blocks']:
                print("Warning: No blocks were generated")
                return

            # Get all logical blocks from the processor
            blocks = result['blocks']
            print(f"Generated {len(blocks)} logical blocks")
            
            # Track which physical rows are represented in blocks
            represented_rows = set()
            total_block_rows = 0
            
            # Diagnostic output for each block
            print("\n=== DIAGNOSTIC OUTPUT FOR LOGICAL BLOCKS ===")
            for i, block in enumerate(blocks):
                print(f"\nBlock {i+1} (ID: {block['block_id']}):")
                print(f"  Page: {block['page_number']}")
                print(f"  Type: {block['type']}")
                print(f"  Text content: {block['text_content'][:100]}...")  # First 100 chars
                print(f"  Physical rows in block: {len(block.get('physical_rows', []))}")
                
                # Display physical rows for this block with their display IDs
                if 'physical_rows' in block and block['physical_rows']:
                    print("  Physical rows:")
                    for j, row_data in enumerate(block['physical_rows']):
                        row_id = row_data.get('row_id', 'unknown')
                        display_id = row_display_ids.get(row_id, 'unknown')
                        print(f"    {display_id}: {row_data.get('text', '')[:80]}...")
                        represented_rows.add(row_id)
                        total_block_rows += 1
                else:
                    print("  Physical rows: None")
            
            # Verification tests for traceability
            print("\n=== VERIFICATION TESTS ===")
            
            # Test 1: Every input physical row should appear in exactly one LogicalBlock
            all_input_row_ids = {row.row_id for row in physical_rows}
            print(f"Total input PhysicalRows: {len(all_input_row_ids)}")
            print(f"Total represented PhysicalRows: {len(represented_rows)}")
            print(f"Total PhysicalRows in blocks: {total_block_rows}")
            
            # Test 2: Check if all rows are represented exactly once
            missing_rows = all_input_row_ids - represented_rows
            extra_rows = represented_rows - all_input_row_ids
            duplicate_rows = represented_rows.intersection(all_input_row_ids) - represented_rows.symmetric_difference(all_input_row_ids)
            
            print(f"Missing rows (not in any block): {len(missing_rows)}")
            if missing_rows:
                print(f"  Missing row IDs: {list(missing_rows)[:5]}...")  # Show first 5
                
            print(f"Extra rows (in blocks but not input): {len(extra_rows)}")
            if extra_rows:
                print(f"  Extra row IDs: {list(extra_rows)[:5]}...")  # Show first 5
                
            # Test 3: Verify text traceability - check that all physical row texts are in block text_content
            print("\nText Traceability Check:")
            all_physical_text = " ".join(row.text for row in physical_rows)
            all_block_texts = " ".join(block['text_content'] for block in blocks)
            print(f"Total physical text length: {len(all_physical_text)}")
            print(f"Total block text length: {len(all_block_texts)}")
            
            # Check that each physical row's text is present in at least one block
            missing_text_rows = []
            for row in physical_rows:
                if row.text.strip() and row.text not in all_block_texts:
                    # Try with partial match since spaces may be different
                    found = False
                    for block in blocks:
                        if row.text in block['text_content']:
                            found = True
                            break
                    if not found:
                        missing_text_rows.append(row)
            
            print(f"Physical rows whose text is NOT found in any block: {len(missing_text_rows)}")
            if missing_text_rows:
                for row in missing_text_rows[:3]:  # Show first 3
                    print(f"  Missing: '{row.text[:50]}...'")
            
            # Summary of verification results
            print("\n=== SUMMARY ===")
            if len(represented_rows) == len(all_input_row_ids):
                print("✓ All PhysicalRows are represented exactly once")
            else:
                print("✗ Some PhysicalRows are missing or duplicated")
                
            if len(missing_rows) == 0 and len(extra_rows) == 0:
                print("✓ No rows are missing or extra in block representation")
            else:
                print("✗ Row representation issues detected")
            
            if len(missing_text_rows) == 0:
                print("✓ All physical row texts are found in block content")
            else:
                print("✗ Some physical row texts are missing from block content")
                
            # Final statistics
            print(f"\nFinal Statistics:")
            print(f"  Input PhysicalRows: {len(physical_rows)}")
            print(f"  Generated LogicalBlocks: {len(blocks)}")
            print(f"  Pages processed: {len(pages)}")
            print(f"  Total rows in blocks: {total_block_rows}")

            # Assertions for basic validation
            self.assertEqual(len(represented_rows), len(all_input_row_ids), "All input rows should be represented exactly once")
            self.assertEqual(total_block_rows, len(physical_rows), "Total rows in blocks should match input rows")
            self.assertGreater(len(blocks), 0, "Should generate at least one logical block")
            self.assertEqual(len(pages), len(set(row.page_number for row in physical_rows)), "All pages should be processed")
            
        except Exception as e:
            print(f"Error during processing: {e}")
            raise

if __name__ == '__main__':
    unittest.main()