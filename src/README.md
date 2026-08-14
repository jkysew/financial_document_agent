# PDF Evidence Tools for Financial Document Agent

This module provides functionality to extract evidence from PDF documents using actual PDF file reading capabilities.

## Requirements

- PyMuPDF (`fitz`) - install with `pip install PyMuPDF`

## Features

- **Actual PDF Reading**: Reads real PDF files, not simulated data
- **Page Evidence Extraction**: Gets text and dimensions for each page
- **Physical Row Extraction**: Extracts individual rows with coordinates
- **Text Search**: Searches across all pages in the document
- **Coordinate-based Retrieval**: Finds evidence within specific coordinate regions
- **Evidence Source Creation**: Converts physical rows to evidence sources

## Usage Example

```python
from src.evidence_tools import PDFEvidenceRetriever

# Initialize with a PDF file path
retriever = PDFEvidenceRetriever("path/to/document.pdf")

# Get page evidence
page_evidence = retriever.get_page_evidence(1)

# Extract physical rows from a page
rows = retriever.get_physical_rows_on_page(1)

# Search text across document
results = retriever.search_text("fee")

# Close when done
retriever.close()