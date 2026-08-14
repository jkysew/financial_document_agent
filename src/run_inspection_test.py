#!/usr/bin/env python3
"""
Simple test runner for inspection functionality
"""

import os
import sys
import json

# Add src to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.inspection_tool import smoke_test_inspection

def main():
    print("=== Running Inspection Tool Tests ===")
    
    # Run smoke test
    result = smoke_test_inspection()
    
    if result and os.path.exists(result):
        print(f"✓ Test passed: Created {result}")
        
        # Read and display sample of the JSON structure
        try:
            with open(result, 'r') as f:
                data = json.load(f)
            
            print("\n=== Sample JSON Structure ===")
            print(f"Document path: {data['document_info']['document_path']}")
            print(f"Page count: {data['document_info']['page_count']}")
            print(f"Number of pages in export: {len(data['pages'])}")
            
            if len(data['pages']) > 0:
                first_page = data['pages'][0]
                print(f"\nFirst page info:")
                print(f"  Page number: {first_page['page_number']}")
                print(f"  Number of physical rows: {len(first_page['physical_rows'])}")
                
                if len(first_page['physical_rows']) > 0:
                    first_row = first_page['physical_rows'][0]
                    print(f"  First row ID: {first_row['row_id']}")
                    print(f"  Row text preview: {first_row['text'][:100]}...")
                    print(f"  Coordinates: {first_row['coordinates']}")
                    print(f"  Word count: {len(first_row['words'])}")
            
            print("\n✓ All tests passed successfully!")
            
        except Exception as e:
            print(f"Error reading JSON file: {e}")
    else:
        print("✗ Test failed")

if __name__ == "__main__":
    main()