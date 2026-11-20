import pdfplumber
import re
import pandas as pd

def clean_page_text(text):
    """
    Cleans out standard PDF artifacts like page numbers and footnotes.
    Modify the regex based on your specific PDF's footnote formatting.
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        # Skip standalone page numbers
        if re.match(r'^\d+$', line.strip()):
            continue
        # Skip footnotes typically starting with a number and a space at the bottom
        if re.match(r'^\d+\.\s+Subs\.', line.strip()) or re.match(r'^\d+\.\s+Ins\.', line.strip()):
            continue
            
        cleaned_lines.append(line.strip())
        
    return ' '.join(cleaned_lines)

def parse_ipc_pdf(pdf_path, output_csv="ipc_parsed.csv"):
    """
    Extracts Chapters and Sections from an IPC PDF and saves to CSV.
    """
    parsed_data = []
    full_text = ""

    print(f"Reading PDF: {pdf_path}...")
    
    # 1. Extract and clean text from all pages
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text = page.extract_text()
            if raw_text:
                full_text += clean_page_text(raw_text) + " "

    print("Parsing text into Chapters and Sections...")

    # 2. Define State Variables
    current_chapter = ""
    current_chapter_name = ""
    current_section = ""
    current_section_name = ""
    current_description = ""

    # 3. Regex Patterns
    # Matches "CHAPTER I INTRODUCTION" or "CHAPTER IVA"
    chapter_pattern = re.compile(r'(CHAPTER\s+[A-ZIVX]+)\s+([A-Z\s]+?)(?=\s+\d+\.)')
    
    # Matches "1. Title of section.—Description" or "124A. Sedition.—"
    # Looking for a number (with optional letter), a dot, text, and an em-dash/en-dash
    section_pattern = re.compile(r'(\d+[A-Z]?)\.\s+(.*?)\.—(.*?)(?=\s+\d+[A-Z]?\.\s+|$)', re.DOTALL)

    # 4. Process Chapters
    # Split the document by "CHAPTER" to isolate chapter blocks
    chapter_blocks = re.split(r'(?=CHAPTER\s+[A-ZIVX]+)', full_text)

    for block in chapter_blocks:
        if not block.strip():
            continue

        # Extract Chapter Info
        chapter_match = chapter_pattern.search(block)
        if chapter_match:
            current_chapter = chapter_match.group(1).strip()
            current_chapter_name = chapter_match.group(2).strip()
        else:
            # Fallback if no chapter header is found at the very beginning
            if not current_chapter:
                current_chapter = "PRELIMINARY"

        # Extract Sections within this Chapter
        # We use finditer to iterate through all sections in the block
        for sec_match in section_pattern.finditer(block):
            section_num = sec_match.group(1).strip()
            section_title = sec_match.group(2).strip()
            section_desc = sec_match.group(3).strip()

            # Clean up description formatting
            section_desc = re.sub(r'\s+', ' ', section_desc).strip()

            parsed_data.append({
                "Chapter": current_chapter,
                "Chapter_name": current_chapter_name,
                "Section": section_num,
                "Section_name": section_title,
                "Description": section_desc
            })

    # 5. Export to DataFrame and CSV
    df = pd.DataFrame(parsed_data)
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"Successfully parsed {len(df)} sections. Saved to {output_csv}.")
    
    return df

# --- Execution ---
if __name__ == "__main__":
    # Replace 'ipc.pdf' with the actual path to your downloaded PDF file
    pdf_filename = ".pdf" 
    
    try:
        df_result = parse_ipc_pdf(pdf_filename, "parsed_ipc_data.csv")
        print(df_result.head(10)) # Preview the first 10 rows
    except FileNotFoundError:
        print(f"Error: Could not find the file '{pdf_filename}'. Please ensure the file is in the same folder as this script.")