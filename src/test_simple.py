"""
Simple test to verify the PDF evidence tools work with the actual PDF file
"""

from src.evidence_tools import PDFEvidenceRetriever

def main():
    # Test with the actual PDF
    pdf_path = "documents/ing_luxembourg.pdf"
    
    try:
        retriever = PDFEvidenceRetriever(pdf_path)
        
        print(f"PDF loaded successfully: {pdf_path}")
        print(f"Number of pages: {retriever.page_count}")
        
        # Test getting first page evidence
        page_evidence = retriever.get_page_evidence(1)
        print(f"Page 1 - Text length: {len(page_evidence.text)}")
        print(f"Page 1 - Dimensions: {page_evidence.dimensions}")
        
        # Test getting physical rows
        rows = retriever.get_physical_rows_on_page(1)
        print(f"Page 1 - Number of rows: {len(rows)}")
        
        if len(rows) > 0:
            first_row = rows[0]
            print(f"First row text: {first_row.text[:100]}...")
            print(f"First row coordinates: {first_row.coordinates}")
        
        # Test search
        results = retriever.search_text("fee")
        print(f"Search results for 'fee': {len(results)} matches found")
        
        retriever.close()
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    main()