"""
Evidence tools for Financial Document Agent v4 - Actual PDF Implementation
"""

import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
from src.models import PhysicalRow, EvidenceSource, LogicalDocumentBlock, VisualSpan
from dataclasses import dataclass


@dataclass
class PageEvidence:
    """Evidence from a single page"""
    page_number: int
    text: str
    dimensions: Dict[str, float]  # {width, height}
    raw_evidence: str


class PDFEvidenceRetriever:
    """Retrieves evidence directly from actual PDF files using PyMuPDF"""
    
    def __init__(self, pdf_path: str):
        """
        Initialize with a path to the PDF file
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        self.pdf_path = pdf_path
        self._pdf_document = None
        self._page_count = None
    
    @property
    def pdf_document(self):
        """Lazy load the PDF document"""
        if self._pdf_document is None:
            self._pdf_document = fitz.open(self.pdf_path)
        return self._pdf_document
    
    @property
    def page_count(self):
        """Get actual number of pages in the PDF"""
        if self._page_count is None:
            self._page_count = self.pdf_document.page_count
        return self._page_count
    
    def get_page_evidence(self, page_number: int) -> PageEvidence:
        """
        Get evidence from a specific page
        
        Args:
            page_number (int): Page number to retrieve
            
        Returns:
            PageEvidence: Page evidence including text, dimensions, and raw content
        """
        if page_number < 1 or page_number > self.page_count:
            raise ValueError(f"Page number {page_number} out of range [1, {self.page_count}]")
        
        # Get the page
        page = self.pdf_document[page_number - 1]
        
        # Extract text
        text = page.get_text()
        
        # Get page dimensions (in points)
        rect = page.rect
        dimensions = {
            'width': float(rect.width),
            'height': float(rect.height)
        }
        
        # Get raw evidence (including layout information)
        raw_evidence = text
        
        return PageEvidence(
            page_number=page_number,
            text=text,
            dimensions=dimensions,
            raw_evidence=raw_evidence
        )
    
    def get_all_pages(self) -> List[PageEvidence]:
        """
        Discover all pages in the PDF and retrieve their evidence
        
        Returns:
            List[PageEvidence]: List of evidence from all pages
        """
        pages = []
        for page_num in range(1, self.page_count + 1):
            pages.append(self.get_page_evidence(page_num))
        return pages
    def get_physical_rows_on_page(self, page_number: int) -> List[PhysicalRow]:
        """
        Extract physical rows from a specific page using existing PDF extraction capabilities
        
        Args:
            page_number (int): Page number to extract rows from
            
        Returns:
            List[PhysicalRow]: List of physical rows extracted from the page
        """
        if page_number < 1 or page_number > self.page_count:
            raise ValueError(f"Page number {page_number} out of range [1, {self.page_count}]")
        
        page = self.pdf_document[page_number - 1]
        
        # Extract text with word positions
        words = page.get_text("words")
        
        # Sort words by y-coordinate (top to bottom) and then x-coordinate (left to right)
        words.sort(key=lambda w: (w[1], w[0]))
        
        # Group words into rows based on y-coordinate proximity
        rows = []
        current_row_words = []
        current_row_y = None
        y_tolerance = 5.0  # Tolerance for considering words on same line (in points)
        
        for word in words:
            x0, y0, x1, y1, text = word[:5]
            y_center = (y0 + y1) / 2  # Calculate vertical center of the word
            
            # If this is the first word in a potential row or if we're starting a new row
            if current_row_y is None:
                current_row_y = y_center
            elif abs(y_center - current_row_y) > y_tolerance:
                # Save the previous row if it exists
                if current_row_words:
                    rows.append(self._create_physical_row_from_words(current_row_words, page_number))
                    current_row_words = []
                # Start a new row with this word
                current_row_y = y_center
            
            current_row_words.append(word)
        
        # Add the last row if it exists
        if current_row_words:
            rows.append(self._create_physical_row_from_words(current_row_words, page_number))
        
        return rows
        
    def _create_physical_row_from_words(self, words: List, page_number: int) -> PhysicalRow:
        """Create a PhysicalRow from a list of words"""
        # Get bounding box for the row
        x_coords = [word[0] for word in words] + [word[2] for word in words]
        y_coords = [word[1] for word in words] + [word[3] for word in words]
        
        coordinates = {
            'x1': min(x_coords),
            'y1': min(y_coords),
            'x2': max(x_coords),
            'y2': max(y_coords)
        }
        
        # Combine text from all words
        text = " ".join([word[4] for word in words])
        
        # Create individual word objects
        word_objects = [
            {
                'text': word[4],
                'x': word[0],
                'y': word[1]
            }
            for word in words
        ]
        
        return PhysicalRow(
            page_number=page_number,
            coordinates=coordinates,
            text=text,
            words=word_objects
        )

    def _extract_visual_spans(self, page) -> List[VisualSpan]:
        """Extract visual spans from a PDF page.

        Args:
            page: A PyMuPDF Page object.

        Returns:
            List[VisualSpan]: List of visual spans extracted from the page.
        """
        spans_list = []
        text_dict = page.get_text("dict")

        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"]
                    if not text:
                        continue
                    bbox = {
                        "x0": span["bbox"][0],
                        "y0": span["bbox"][1],
                        "x1": span["bbox"][2],
                        "y1": span["bbox"][3],
                    }
                    spans_list.append(VisualSpan(
                        text=text,
                        font_family=span["font"],
                        font_size=span["size"],
                        font_flags=int(span["flags"]),
                        color=span["color"],
                        bbox=bbox,
                    ))

        return spans_list
    
    def search_text(self, query: str) -> List[Tuple[int, str]]:
        """
        Search for text across all pages in the document
        
        Args:
            query (str): Text to search for
            
        Returns:
            List[Tuple[int, str]]: List of (page_number, matched_text) tuples
        """
        results = []
        
        # Search each page
        for page_num in range(1, self.page_count + 1):
            page_evidence = self.get_page_evidence(page_num)
            if query.lower() in page_evidence.text.lower():
                # Find all occurrences
                start = 0
                while True:
                    pos = page_evidence.text.lower().find(query.lower(), start)
                    if pos == -1:
                        break
                    # Get a context around the match (50 chars before and after)
                    context_start = max(0, pos - 50)
                    context_end = min(len(page_evidence.text), pos + len(query) + 50)
                    matched_text = page_evidence.text[context_start:context_end].strip()
                    results.append((page_num, matched_text))
                    start = pos + 1
        
        return results
    
    def get_evidence_from_coordinates(self, page_number: int, x1: float, y1: float, 
                                    x2: float, y2: float) -> List[PhysicalRow]:
        """
        Get physical rows from a coordinate region on a page
        
        Args:
            page_number (int): Page number
            x1 (float): Top-left X coordinate
            y1 (float): Top-left Y coordinate
            x2 (float): Bottom-right X coordinate
            y2 (float): Bottom-right Y coordinate
            
        Returns:
            List[PhysicalRow]: Physical rows found in the coordinate region
        """
        if page_number < 1 or page_number > self.page_count:
            raise ValueError(f"Page number {page_number} out of range [1, {self.page_count}]")
        
        # Get all physical rows on the page
        rows = self.get_physical_rows_on_page(page_number)
        
        # Filter by coordinates
        matching_rows = []
        for row in rows:
            # Check if row's bounding box intersects with specified region
            if (row.coordinates['x1'] <= x2 and row.coordinates['x2'] >= x1 and 
                row.coordinates['y1'] <= y2 and row.coordinates['y2'] >= y1):
                matching_rows.append(row)
        
        return matching_rows
    
    def get_evidence_source_from_physical_row(self, row: PhysicalRow) -> EvidenceSource:
        """
        Create an evidence source from a physical row
        
        Args:
            row (PhysicalRow): Physical row to convert
            
        Returns:
            EvidenceSource: Evidence source object
        """
        return EvidenceSource(
            source_type="text",
            page_number=row.page_number,
            coordinates=row.coordinates,
            content=row.text,
            context=row.text,  # For now, use the same text as context
            evidence_id=None  # Will be auto-generated
        )
    
    def get_evidence_source_from_coordinate_region(self, page_number: int, 
                                                 x1: float, y1: float, 
                                                 x2: float, y2: float) -> EvidenceSource:
        """
        Create an evidence source from a coordinate region
        
        Args:
            page_number (int): Page number
            x1 (float): Top-left X coordinate
            y1 (float): Top-left Y coordinate
            x2 (float): Bottom-right X coordinate
            y2 (float): Bottom-right Y coordinate
            
        Returns:
            EvidenceSource: Evidence source object
        """
        # Get text content for this region
        page = self.pdf_document[page_number - 1]
        rect = fitz.Rect(x1, y1, x2, y2)
        text = page.get_text("text", clip=rect).strip()
        
        return EvidenceSource(
            source_type="coordinate_region",
            page_number=page_number,
            coordinates={'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
            content=text,
            context=text,
            evidence_id=None  # Will be auto-generated
        )
    
    def close(self):
        """Close the PDF document"""
        if self._pdf_document:
            self._pdf_document.close()
            self._pdf_document = None