"""
Temporary analysis script for visual_span_inspection.json
Reports basic vertical-gap statistics across all pages/rows.
Does NOT modify any existing source files.
"""

import json
import os
import sys

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def percentile(sorted_vals: list, p: float) -> float:
    """Compute the p-th percentile of *sorted_vals* (p in [0, 100])."""
    if not sorted_vals:
        return 0.0
    k = (p / 100.0) * (len(sorted_vals) - 1)
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return float(sorted_vals[f])
    d = k - f
    return sorted_vals[f] + d * (sorted_vals[c] - sorted_vals[f])


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    json_path = os.path.join(repo_root, "data", "visual_span_inspection.json")

    if not os.path.exists(json_path):
        print(f"ERROR: cannot find {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    pages = data.get("pages", [])
    total_pages = len(pages)
    total_rows = 0
    all_gaps: list[float] = []
    all_pairs: list[tuple[int, str, str, float]] = []  # (page, prev_text, curr_text, gap)

    for page in pages:
        pnum = page["page_number"]
        rows = page.get("rows", [])
        total_rows += len(rows)

        if len(rows) < 2:
            continue

        # Sort by y1
        sorted_rows = sorted(rows, key=lambda r: r["coordinates"]["y1"])

        for i in range(1, len(sorted_rows)):
            prev = sorted_rows[i - 1]
            curr = sorted_rows[i]
            gap = curr["coordinates"]["y1"] - prev["coordinates"]["y2"]
            all_gaps.append(gap)
            all_pairs.append((
                pnum,
                prev.get("text", "")[:80],
                curr.get("text", "")[:80],
                gap,
            ))

    # Sort gaps for percentiles
    all_gaps_sorted = sorted(all_gaps)

    print("=" * 90)
    print("DOCUMENT-WIDE VERTICAL GAP ANALYSIS")
    print("=" * 90)
    print(f"  Total pages:                {total_pages}")
    print(f"  Total rows:                 {total_rows}")
    print(f"  Adjacent row pairs:         {len(all_gaps)}")
    print()
    print("Gap statistics:")
    if all_gaps_sorted:
        print(f"  Minimum gap:                {min(all_gaps):.4f}")
        print(f"  Maximum gap:                {max(all_gaps):.4f}")
        print(f"  Median gap (p50):           {percentile(all_gaps_sorted, 50):.4f}")
        print(f"  25th percentile (p25):      {percentile(all_gaps_sorted, 25):.4f}")
        print(f"  75th percentile (p75):      {percentile(all_gaps_sorted, 75):.4f}")
        print(f"  90th percentile (p90):      {percentile(all_gaps_sorted, 90):.4f}")
    else:
        print("  No adjacent row pairs found.")

    # 10 smallest gaps
    print()
    print("=" * 90)
    print("10 SMALLEST GAPS (strong vertical continuity candidates)")
    print("=" * 90)
    for pnum, prev_txt, curr_txt, gap in sorted(all_pairs, key=lambda x: x[3])[:10]:
        print(f"  Page {pnum}: gap={gap:8.4f}  \"{prev_txt}\" -> \"{curr_txt}\"")

    # 10 largest gaps
    print()
    print("=" * 90)
    print("10 LARGEST GAPS (likely block/section boundaries)")
    print("=" * 90)
    for pnum, prev_txt, curr_txt, gap in sorted(all_pairs, key=lambda x: -x[3])[:10]:
        print(f"  Page {pnum}: gap={gap:8.4f}  \"{prev_txt}\" -> \"{curr_txt}\"")

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()