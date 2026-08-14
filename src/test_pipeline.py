"""
Test script for Financial Document Agent v3 pipeline
"""

from src.models import PhysicalRow
from src.document_processor import DocumentProcessor


def main():
    print("Financial Document Agent v3 Pipeline Test")
    print("=" * 50)
    
    # Create some mock physical rows (simulating extracted PDF data)
    physical_rows = [
        PhysicalRow(
            page_number=1,
            coordinates={'x1': 50, 'y1': 100, 'x2': 500, 'y2': 130},
            text="Research fee € 75/hour + VAT*",
            words=[{'text': "Research", 'x': 50, 'y': 100}, {'text': "fee", 'x': 120, 'y': 100}]
        ),
        PhysicalRow(
            page_number=1,
            coordinates={'x1': 50, 'y1': 140, 'x2': 500, 'y2': 170},
            text="External research fee reinvoicing the customer at cost*",
            words=[{'text': "External", 'x': 50, 'y': 140}, {'text': "research", 'x': 130, 'y': 140}]
        ),
        PhysicalRow(
            page_number=1,
            coordinates={'x1': 50, 'y1': 180, 'x2': 500, 'y2': 210},
            text="* within the limit of the law, research fees (internal + external) cannot exceed 10% of the assets with a max of EUR 25 000",
            words=[{'text': "within", 'x': 50, 'y': 180}, {'text': "limit", 'x': 110, 'y': 180}]
        ),
        PhysicalRow(
            page_number=1,
            coordinates={'x1': 50, 'y1': 220, 'x2': 500, 'y2': 250},
            text="Liquidation of assets or conversion of currencies Cf standard pricing",
            words=[{'text': "Liquidation", 'x': 50, 'y': 220}, {'text': "assets", 'x': 140, 'y': 220}]
        )
    ]
    
    # Process the document
    processor = DocumentProcessor()
    result = processor.process_document(physical_rows)
    
    # Display results
    print(f"\nProcessing completed successfully!")
    print(f"Total logical blocks: {result['summary']['total_blocks']}")
    print(f"Total fee candidates: {result['summary']['total_candidates']}")
    
    print("\nDetailed Results:")
    print("-" * 30)
    
    for block in result['blocks']:
        print(f"\nBlock ID: {block['block_id']}")
        print(f"Type: {block['type']}")
        print(f"Page: {block['page_number']}")
        print(f"Status: {block['status']}")
        print(f"Confidence: {block['confidence_score']:.2f}")
        print(f"Text content: {block['text_content'][:100]}...")
        
        if block['fee_candidates']:
            print("Fee Candidates:")
            for candidate in block['fee_candidates']:
                print(f"  - {candidate['description']}")
                if candidate['amount']:
                    print(f"    Amount: {candidate['amount']} {candidate['currency']}")
                print(f"    Type: {candidate['pricing_type']}")
                print(f"    Status: {candidate['status']}")
                print(f"    Confidence: {candidate['confidence_score']:.2f}")


if __name__ == "__main__":
    main()