"""
Inspection tool for exporting PDF evidence to JSON for visual inspection.
This tool uses the existing PDF evidence retrieval capabilities to produce
deterministic output that can be visually inspected.
"""

import os
import json
from typing import Dict, Any, List
from src.evidence_tools import PDFEvidenceRetriever
from src.models import PhysicalRow

def export_evidence_to_json(pdf_path: str, output_dir: str = "data/evidence") -> str:
    """
    Export evidence from a PDF document to JSON for inspection.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to save the JSON output
        
    Returns:
        str: Path to the generated JSON file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the evidence retriever
    retriever = PDFEvidenceRetriever(pdf_path)
    
    try:
        # Get document information
        document_info = {
            "document_path": pdf_path,
            "page_count": retriever.page_count
        }
        
        # Get all pages and their physical rows
        pages_data = []
        for page_num in range(1, retriever.page_count + 1):
            # Get physical rows for this page
            rows = retriever.get_physical_rows_on_page(page_num)
            
            page_data = {
                "page_number": page_num,
                "physical_rows": []
            }
            
            # Process each row
            for row in rows:
                row_data = {
                    "row_id": row.row_id,  # Use the actual row_id from Phase 1 models
                    "page_number": row.page_number,
                    "coordinates": row.coordinates,
                    "text": row.text,
                    "words": row.words
                }
                page_data["physical_rows"].append(row_data)
            
            pages_data.append(page_data)
        
        # Create the complete export structure
        export_data = {
            "document_info": document_info,
            "pages": pages_data
        }
        
        # Generate output filename - use the specific name requested
        pdf_filename = os.path.basename(pdf_path).replace(".pdf", "")
        output_file = os.path.join(output_dir, f"{pdf_filename}_evidence_output.json")
        
        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return output_file
        
    finally:
        # Always close the retriever
        retriever.close()

# Simple smoke test function
def smoke_test_inspection():
    """Run a smoke test using the real PDF document."""
    pdf_path = "documents/ing_luxembourg.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return None
    
    try:
        output_file = export_evidence_to_json(pdf_path)
        print(f"Successfully exported evidence to: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error during smoke test: {e}")
        return None

if __name__ == "__main__":
    # Run smoke test
    smoke_test_inspection()