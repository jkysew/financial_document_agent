"""
Standalone inspection/export script for VisualSpan-to-PhysicalRow evidence data.

Reads the actual ING PDF, extracts all physical rows with their visual spans,
and writes structured evidence to data/visual_span_inspection.json.

This is read-only from the perspective of the extraction pipeline - it only
consumes output from existing code without modifying it.
"""

import json
import os
import sys
from dataclasses import asdict

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.evidence_tools import PDFEvidenceRetriever


def _physical_row_to_dict(row) -> dict:
    """Convert a PhysicalRow to a serializable dictionary."""
    return {
        "page_number": row.page_number,
        "text": row.text,
        "coordinates": row.coordinates,
        "words": row.words,
        "visual_spans": [
            {
                "text": span.text,
                "font_family": span.font_family,
                "font_size": span.font_size,
                "font_flags": span.font_flags,
                "color": span.color,
                "bbox": span.bbox,
            }
            for span in row.visual_spans
        ],
    }


def export_visual_span_inspection(pdf_path: str, output_path: str) -> dict:
    """
    Extract all physical rows and visual spans from every page of the PDF.

    Args:
        pdf_path: Path to the ING PDF file.
        output_path: Path where the JSON will be written.

    Returns:
        The inspection dictionary that was written.
    """
    retriever = PDFEvidenceRetriever(pdf_path)

    pages_data = []
    for page_num in range(1, retriever.page_count + 1):
        rows = retriever.get_physical_rows_on_page(page_num)
        pages_data.append({
            "page_number": page_num,
            "rows": [_physical_row_to_dict(r) for r in rows],
        })

    inspection = {
        "document": {
            "source": pdf_path,
            "page_count": retriever.page_count,
        },
        "pages": pages_data,
    }

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(inspection, f, indent=2, ensure_ascii=False)

    retriever.close()
    return inspection


def report_statistics(inspection: dict):
    """Print summary statistics from the generated inspection JSON."""
    doc = inspection["document"]
    print(f"Document source: {doc['source']}")
    print(f"Page count: {doc['page_count']}")

    total_rows = 0
    total_spans = 0
    rows_with_spans = 0

    for page in inspection["pages"]:
        page_num = page["page_number"]
        page_rows = len(page["rows"])
        page_spans = sum(len(r["visual_spans"]) for r in page["rows"])
        page_rows_with_spans = sum(1 for r in page["rows"] if len(r["visual_spans"]) > 0)

        total_rows += page_rows
        total_spans += page_spans
        rows_with_spans += page_rows_with_spans

        print(f"  Page {page_num}: {page_rows} rows, {page_spans} spans, {page_rows_with_spans} rows with spans")

    print()
    print(f"Total physical rows: {total_rows}")
    print(f"Total visual spans: {total_spans}")
    print(f"Total rows containing visual spans: {rows_with_spans}")


if __name__ == "__main__":
    # Locate the ING PDF from the project's documents folder
    pdf_path = os.path.join(project_root, "documents", "ing_luxembourg.pdf")
    output_path = os.path.join(project_root, "data", "visual_span_inspection.json")

    inspection = export_visual_span_inspection(pdf_path, output_path)
    print(f"Written inspection JSON to: {output_path}")
    print()
    report_statistics(inspection)