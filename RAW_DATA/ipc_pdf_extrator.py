import re
import json
import pandas as pd
import pypdf

def parse_ipc_arrangement_text(raw_text: str) -> pd.DataFrame:
    """
    Parses raw text from the IPC 'ARRANGEMENT OF SECTIONS' table of contents.
    
    Returns:
        pd.DataFrame: Structured table with Chapter, Subheading, Section Number, and Title.
    """
    lines = raw_text.splitlines()
    data = []
    
    current_chapter_num = ""
    current_chapter_title = ""
    current_subheading = ""
    
    # Patterns
    chap_pattern = re.compile(r'^\s*(CHAPTER\s+[IVXLCDMAB]+)\s*$', re.IGNORECASE)
    sec_pattern = re.compile(r'^\s*(\d+[A-Z]*)\.\s*(.*)')
    source_tag_pattern = re.compile(r'^\s*\\', re.IGNORECASE)
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines, page numbers, dividers, or source tags
        if not line or line.isdigit() or line.startswith("___") or source_tag_pattern.match(line):
            i += 1
            continue
            
        # 1. Match Chapter Header (e.g., CHAPTER I, CHAPTER VA)
        m_chap = chap_pattern.match(line)
        if m_chap:
            current_chapter_num = m_chap.group(1).upper()
            i += 1
            # Accumulate next line(s) for chapter title until section/subheading marker
            title_parts = []
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt or nxt.isdigit() or nxt.startswith("___") or source_tag_pattern.match(nxt):
                    i += 1
                    continue
                if (sec_pattern.match(nxt) or nxt == "SECTIONS" or 
                    nxt.startswith("CHAPTER") or nxt.lower().startswith("of ") or 
                    nxt.lower().startswith("or ")):
                    break
                title_parts.append(nxt)
                i += 1
            current_chapter_title = " ".join(title_parts)
            current_subheading = ""  # Reset subheading when new chapter starts
            continue
            
        # 2. Match Sub-headings (e.g., "Of Hurt", "Of the Right of Private Defence")
        if line.lower().startswith("of ") or line.lower().startswith("or criminal"):
            current_subheading = line
            i += 1
            continue
            
        # 3. Match Section (e.g., "1. Title and extent...", "29A. Electronic record.")
        m_sec = sec_pattern.match(line)
        if m_sec:
            sec_num = m_sec.group(1)
            sec_title = m_sec.group(2).strip()
            
            i += 1
            # Look ahead for wrapped multi-line section titles
            while i < len(lines):
                nxt = lines[i].strip()
                if (not nxt or nxt.isdigit() or nxt == "SECTIONS" or nxt.startswith("___") or
                    source_tag_pattern.match(nxt) or nxt.startswith("CHAPTER") or 
                    sec_pattern.match(nxt) or nxt.lower().startswith("of ")):
                    break
                sec_title += " " + nxt
                i += 1
                
            data.append({
                "chapter_number": current_chapter_num,
                "chapter_title": current_chapter_title,
                "subheading": current_subheading,
                "section_number": sec_num,
                "section_title": sec_title
            })
            continue
            
        i += 1
        
    return pd.DataFrame(data)


def parse_ipc_pdf(pdf_filepath: str, max_index_pages: int = 14) -> pd.DataFrame:
    """
    Extracts text from the IPC PDF file and parses the ARRANGEMENT OF SECTIONS pages.
    """
    reader = pypdf.PdfReader(pdf_filepath)
    extracted_text = ""
    
    # Arrangement of sections is contained in the first ~13 pages
    num_pages_to_read = min(max_index_pages, len(reader.pages))
    for page_idx in range(num_pages_to_read):
        page_text = reader.pages[page_idx].extract_text()
        extracted_text += page_text + "\n"
        
    return parse_ipc_arrangement_text(extracted_text)


if __name__ == "__main__":
    # Example 1: Extracting directly from PDF
    pdf_filename = "indian-penal-code-sections-of-ipc.pdf"
    
    try:
        df_sections = parse_ipc_pdf(pdf_filename)
        print(f"Successfully extracted {len(df_sections)} sections.")
        print("\nFirst 10 parsed sections:")
        print(df_sections[["chapter_number", "section_number", "section_title"]].head(10))
        
        # Export options
        df_sections.to_csv("IPC_Arrangement_of_Sections.csv", index=False)
        df_sections.to_json("IPC_Arrangement_of_Sections.json", orient="records", indent=2)
        print("\nSaved to 'IPC_Arrangement_of_Sections.csv' and 'IPC_Arrangement_of_Sections.json'")

    except FileNotFoundError:
        print(f"PDF file '{pdf_filename}' not found. You can pass raw string text to `parse_ipc_arrangement_text(text)` instead.")