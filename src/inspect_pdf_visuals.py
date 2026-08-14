import fitz
import sys

# Open the actual PDF
pdf_path = 'documents/ing_luxembourg.pdf'
doc = fitz.open(pdf_path)

print('=== ING Luxembourg PDF Analysis ===')
print(f'Pages: {doc.page_count}')

# Analyze first few pages to understand structure
for page_num in range(min(5, doc.page_count)):
    print(f'\n--- Page {page_num + 1} ---')
    page = doc[page_num]
    
    # Get rich text with spans
    try:
        text_dict = page.get_text('dict')
        if 'blocks' in text_dict:
            print(f'Blocks: {len(text_dict["blocks"])}')
            
            # Print detailed information for first few blocks/lines/spans
            block_count = 0
            for block in text_dict['blocks']:
                if 'lines' in block:
                    line_count = 0
                    for line in block['lines']:
                        if 'spans' in line:
                            span_count = 0
                            for span in line['spans']:
                                print(f'Page {page_num + 1} Block {block_count} Line {line_count} Span {span_count}')
                                print(f'  Text: "{span.get("text", "NO TEXT")}"')
                                print(f'  Size: {span.get("size", "UNKNOWN")}pt')
                                print(f'  Font: {span.get("font", "UNKNOWN")}')
                                print(f'  Flags: {span.get("flags", "NONE")}')
                                print(f'  Color: {span.get("color", "NONE")}')
                                print(f'  Bbox: {span.get("bbox", "NONE")}')
                                print()
                                span_count += 1
                                if span_count > 2:  # Limit output per line
                                    break
                        line_count += 1
                        if line_count > 3:  # Limit output per block
                            break
                block_count += 1
                if block_count > 3:  # Limit blocks per page
                    break
                    
    except Exception as e:
        print(f'Error on page {page_num + 1}: {e}')

doc.close()
print('\n=== Analysis Complete ===')