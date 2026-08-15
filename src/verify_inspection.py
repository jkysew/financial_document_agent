"""Verify the generated visual_span_inspection.json file."""

import json


def main():
    with open("data/visual_span_inspection.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=== JSON Validation ===")
    print("Valid JSON: True")
    print()

    doc = data["document"]
    print(f'Page count: {doc["page_count"]}')

    total_rows = sum(len(p["rows"]) for p in data["pages"])
    total_spans = sum(
        sum(len(r["visual_spans"]) for r in p["rows"]) for p in data["pages"]
    )
    rows_with_spans = sum(
        sum(1 for r in p["rows"] if len(r["visual_spans"]) > 0) for p in data["pages"]
    )

    print(f"Total physical rows: {total_rows}")
    print(f"Total visual spans: {total_spans}")
    print(f"Total rows containing visual spans: {rows_with_spans}")

    print()
    print("=== Page 1, Rows 1-10 ===")
    page1 = data["pages"][0]
    print(f'Page number: {page1["page_number"]}')

    for i, row in enumerate(page1["rows"][:10]):
        print(f"--- Row {i+1} ---")
        print(f'  text: {repr(row["text"])}')
        print(f'  coordinates: {row["coordinates"]}')
        print(f'  words count: {len(row["words"])}')
        print(f'  visual_spans count: {len(row["visual_spans"])}')

        for j, span in enumerate(row["visual_spans"]):
            print(
                f'    Span {j+1}: text={repr(span["text"])}, '
                f'font={span["font_family"]}, size={span["font_size"]}, '
                f'flags={span["font_flags"]}, color={span["color"]}, '
                f'bbox={span["bbox"]}'
            )


if __name__ == "__main__":
    main()