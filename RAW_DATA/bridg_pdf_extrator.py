import pandas as pd
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextLine

input_pdf = "COMPARISONSUMMARYBNStoIPC.pdf"
output_csv = "BNS_to_IPC_Full_Correspondence.csv"

# Horizontal column boundaries (X-coordinates in points)
COL_BNS_MAX = 105.0   # Column 1: BNS Section
COL_SUBJ_MAX = 295.0  # Column 2: Subject
COL_IPC_MAX = 345.0   # Column 3: IPC Section
                      # Column 4: Summary of Comparison (X >= 345.0)

def extract_text_lines(element):
    """Recursively extract text lines with bounding box coordinates."""
    lines = []
    if isinstance(element, LTTextLine):
        text = element.get_text().strip()
        if text:
            bbox = element.bbox  # (X0, Y0, X1, Y1)
            lines.append((bbox[1], bbox[0], bbox[3], bbox[2], text))
    elif hasattr(element, '__iter__'):
        for child in element:
            lines.extend(extract_text_lines(child))
    return lines

all_parsed_rows = []

for page_idx, page_layout in enumerate(extract_pages(input_pdf)):
    raw_lines = extract_text_lines(page_layout)
    
    # Filter out running headers, footers, and table title labels
    lines = []
    for l in raw_lines:
        text = l[4]
        if "CORRESPONDENCE TABLE" in text or "Anil Kishore Yadav" in text or "BHARTATIYA" in text:
            continue
        if text in ["BNS", "Sections/", "Subsecti", "ons", "Subject", "IPC", "Sections", "Summary of comparison"]:
            continue
        lines.append(l)
        
    if not lines:
        continue
        
    # Sort lines from top to bottom (Y1 descending)
    lines.sort(key=lambda x: -x[2])
    
    # Identify BNS section start anchors in Column 1
    anchors = []
    for l in lines:
        if l[1] < COL_BNS_MAX:
            if not anchors or abs(anchors[-1] - l[2]) > 12.0:
                anchors.append(l[2])
                
    if not anchors:
        # If a page contains no new BNS section, append text to the previous page's last row
        if all_parsed_rows:
            last = all_parsed_rows[-1]
            for l in lines:
                x0, text = l[1], l[4]
                if x0 < COL_BNS_MAX: last['bns'].append(text)
                elif x0 < COL_SUBJ_MAX: last['subj'].append(text)
                elif x0 < COL_IPC_MAX: last['ipc'].append(text)
                else: last['summ'].append(text)
        continue
        
    # Handle top-of-page continuation text (lines positioned above the page's first BNS anchor)
    top_anchor = anchors[0]
    continuation_lines = [l for l in lines if l[2] > top_anchor + 10.0]
    page_row_lines = [l for l in lines if l[2] <= top_anchor + 10.0]
    
    if continuation_lines and all_parsed_rows:
        last = all_parsed_rows[-1]
        for l in sorted(continuation_lines, key=lambda x: -x[2]):
            x0, text = l[1], l[4]
            if x0 < COL_BNS_MAX: last['bns'].append(text)
            elif x0 < COL_SUBJ_MAX: last['subj'].append(text)
            elif x0 < COL_IPC_MAX: last['ipc'].append(text)
            else: last['summ'].append(text)

    # Construct vertical Y-buckets for each section row on the page
    buckets = []
    for i, a in enumerate(anchors):
        top = a + 10.0
        bottom = anchors[i+1] + 10.0 if i+1 < len(anchors) else 0.0
        buckets.append({'bns': [], 'subj': [], 'ipc': [], 'summ': [], 'top': top, 'bottom': bottom})
        
    # Assign text lines to their matching row bucket
    for l in page_row_lines:
        y0, x0, y1, x1, text = l
        for b in buckets:
            if b['bottom'] <= y1 <= b['top'] or b['bottom'] <= y0 <= b['top']:
                if x0 < COL_BNS_MAX: b['bns'].append((y1, text))
                elif x0 < COL_SUBJ_MAX: b['subj'].append((y1, text))
                elif x0 < COL_IPC_MAX: b['ipc'].append((y1, text))
                else: b['summ'].append((y1, text))
                break

    for b in buckets:
        all_parsed_rows.append({
            'bns': [t[1] for t in sorted(b['bns'], key=lambda x: -x[0])],
            'subj': [t[1] for t in sorted(b['subj'], key=lambda x: -x[0])],
            'ipc': [t[1] for t in sorted(b['ipc'], key=lambda x: -x[0])],
            'summ': [t[1] for t in sorted(b['summ'], key=lambda x: -x[0])]
        })

# Clean and combine multi-line text into single cell strings
formatted_rows = []
for r in all_parsed_rows:
    bns_val = " ".join(r['bns']).strip()
    subj_val = " ".join(r['subj']).strip()
    ipc_val = " ".join(r['ipc']).strip()
    summ_val = " ".join(r['summ']).strip()
    
    if bns_val and ("1" in bns_val or "2" in bns_val or "Section" in bns_val or len(bns_val) <= 10):
        formatted_rows.append({
            'BNS Section': bns_val,
            'Subject': subj_val,
            'IPC Section': ipc_val,
            'Summary of Comparison': summ_val
        })

# Export dataset to CSV
df = pd.DataFrame(formatted_rows)
df.to_csv(output_csv, index=False)
print(f"Successfully exported {len(df)} accurately aligned rows to '{output_csv}'.")