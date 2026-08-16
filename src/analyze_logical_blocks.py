#!/usr/bin/env python3
"""
Analyze current logical blocks against actual PDF physical rows.

Loads physical rows from the PDF via PDFEvidenceRetriever, groups them using
the current _BLOCK_SPLITTER logic, and reports:
  - Number of blocks per page
  - Rows-per-block distribution
  - Gap values at block boundaries vs within blocks
  - How many rows have visual_spans vs missing span data

Run from project root:
    python -m src.analyze_logical_blocks
"""

import os
import sys
from typing import List, Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.evidence_tools import PDFEvidenceRetriever
from src.logical_block_generator import _BLOCK_SPLITTER, compute_row_relationship


def _collect_rows(pdf_path: str) -> List[Any]:
    """Return all physical rows across all pages, in page-number order."""
    retriever = PDFEvidenceRetriever(pdf_path)
    all_rows: List[Any] = []
    for page_num in range(1, retriever.page_count + 1):
        rows = retriever.get_physical_rows_on_page(page_num)
        all_rows.extend(rows)
    retriever.close()
    return all_rows


def _page_groups(rows: List[Any]) -> Dict[int, List[Any]]:
    """Group rows by page_number, preserving order."""
    groups: Dict[int, List[Any]] = {}
    for r in rows:
        groups.setdefault(r.page_number, []).append(r)
    return groups


def analyze_blocks_for_page(page_num: int, page_rows: List[Any]) -> Dict[str, Any]:
    """Group page_rows with _BLOCK_SPLITTER and return statistics."""
    blocks = _BLOCK_SPLITTER.split(page_rows)
    
    total_rows = len(page_rows)
    num_blocks = len(blocks)
    rows_per_block = [len(b) for b in blocks]
    
    # Collect intra-block gaps and inter-block gaps
    intra_gaps: List[float] = []
    inter_gaps: List[float] = []
    
    for block in blocks:
        for i in range(1, len(block)):
            gap = block[i].coordinates['y1'] - block[i-1].coordinates['y2']
            intra_gaps.append(gap)
    
    # Inter-block gaps: last row of each block to first row of next block (within page)
    idx = 0
    for block in blocks:
        idx += len(block)
        if idx < len(page_rows):
            inter_gap = page_rows[idx].coordinates['y1'] - block[-1].coordinates['y2']
            inter_gaps.append(inter_gap)
    
    # Visual span coverage
    rows_with_spans = 0
    for r in page_rows:
        if hasattr(r, 'visual_spans') and len(r.visual_spans) > 0:
            rows_with_spans += 1
    
    # Sample some row texts from each block (first line of first 5 blocks)
    block_samples = []
    for i, block in enumerate(blocks[:5]):
        sample_text = block[0].text[:60] if block else ""
        sample_bbox = block[0].coordinates if block else {}
        block_samples.append({
            "block_idx": i,
            "num_rows": len(block),
            "first_row_text": sample_text,
            "y_range": (block[0].coordinates['y1'], block[-1].coordinates['y2']) if block else None,
        })
    
    # Sample 5 representative intra-block relationships and inter-block relationships
    intra_rels: List[Dict[str, Any]] = []
    for block in blocks:
        if len(block) >= 2:
            # Sample up to 5 per page total
            sample_points = min(5, len(block) - 1)
            step = max(1, (len(block) - 1) // sample_points)
            for i in range(0, len(block) - 1, step):
                rel = compute_row_relationship(block[i], block[i+1])
                intra_rels.append(rel)
    
    return {
        "page_number": page_num,
        "total_rows": total_rows,
        "num_blocks": num_blocks,
        "rows_per_block": rows_per_block,
        "rows_with_spans": rows_with_spans,
        "intra_gap_stats": _gap_stats(intra_gaps) if intra_gaps else {},
        "inter_gap_stats": _gap_stats(inter_gaps) if inter_gaps else {},
        "block_samples": block_samples,
        "intra_rels_sample": intra_rels[:5],
    }


def _gap_stats(gaps: List[float]) -> Dict[str, Any]:
    """Return median/mean/min/max for a list of gap values."""
    if not gaps:
        return {}
    s = sorted(gaps)
    n = len(s)
    mid = n // 2
    median = s[mid] if n % 2 == 1 else (s[mid-1] + s[mid]) / 2.0
    mean = sum(s) / n
    return {
        "median": round(median, 2),
        "mean": round(mean, 2),
        "min": round(min(s), 2),
        "max": round(max(s), 2),
        "count": n,
    }


def main():
    pdf_path = os.path.join(project_root, "documents", "ing_luxembourg.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF not found at {pdf_path}")
        sys.exit(1)
    
    print(f"Loading physical rows from: {pdf_path}")
    all_rows = _collect_rows(pdf_path)
    print(f"Total rows collected: {len(all_rows)}")
    
    pages = _page_groups(all_rows)
    print(f"Pages with data: {len(pages)}\n")
    
    total_blocks = 0
    total_intra = 0
    total_inter = 0
    
    for page_num in sorted(pages.keys()):
        stats = analyze_blocks_for_page(page_num, pages[page_num])
        total_blocks += stats["num_blocks"]
        
        intra_count = stats["intra_gap_stats"].get("count", 0)
        inter_count = stats["inter_gap_stats"].get("count", 0)
        total_intra += intra_count
        total_inter += inter_count
        
        print(f"=== Page {stats['page_number']} ===")
        print(f"  Total rows: {stats['total_rows']} | Rows with spans: {stats['rows_with_spans']} | Blocks: {stats['num_blocks']}")
        print(f"  Rows per block: {stats['rows_per_block']}")
        
        intra_s = stats["intra_gap_stats"]
        if intra_s:
            print(f"  Intra-block gaps: median={intra_s['median']}, mean={intra_s['mean']}, min={intra_s['min']}, max={intra_s['max']} (n={intra_s['count']})")
        
        inter_s = stats["inter_gap_stats"]
        if inter_s:
            print(f"  Inter-block gaps: median={inter_s['median']}, mean={inter_s['mean']}, min={inter_s['min']}, max={inter_s['max']} (n={inter_s['count']})")
        
        print(f"  Block samples:")
        for s in stats["block_samples"]:
            print(f"    Block {s['block_idx']}: {s['num_rows']} rows, y={s['y_range']}, text='{s['first_row_text']}'")
        
        if stats["intra_rels_sample"]:
            print(f"  Intra-rel sample (first {len(stats['intra_rels_sample'])}):")
            for rel in stats["intra_rels_sample"]:
                print(f"    gap={rel['vertical_gap']:.1f}, overlap={rel['horizontal_overlap']:.2f}, "
                      f"margin_sim={rel['left_margin_similarity']:.2f}, font_sim={rel['font_size_similarity']:.2f}, "
                      f"family_sim={rel['font_family_similarity']:.2f}, bold_sim={rel['bold_similarity']:.1f}")
        
        print()
    
    print(f"=== SUMMARY ===")
    print(f"Total blocks across all pages: {total_blocks}")
    print(f"Total intra-block gaps analyzed: {total_intra}")
    print(f"Total inter-block gaps analyzed: {total_inter}")


if __name__ == "__main__":
    main()