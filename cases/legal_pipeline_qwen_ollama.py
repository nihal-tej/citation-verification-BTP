"""
legal_extract_all.py
Extract page-wise text, judgment metadata, cited cases, and an LLM-as-judge
review from one judgment PDF directly through the Ollama Python client (no OpenAI package/client).
Default model: qwen3.6:35b (override with LLM_MODEL if needed).

Install:
    python -m pip install pymupdf ollama

Run PowerShell:
    $env:LLM_MODEL="your-exact-model-tag-from-ollama-list"
    python legal_extract_all.py "C:\path\to\judgment.pdf"

Outputs are saved beside the PDF in <pdf_name>_extracted/.
LLM review is not proof of correctness; manually verify legal extractions.
"""

import os, re, json, time, argparse
from pathlib import Path
import fitz
import ollama

MODEL = os.getenv("LLM_MODEL", "qwen3.6:35b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
client = ollama.Client(host=OLLAMA_HOST, timeout=180.0)
RETRIES = 2
PAGE_BATCH_SIZE = int(os.getenv("PAGE_BATCH_SIZE", "4"))


def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def ask_json(system, prompt):
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            r = client.chat(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                format="json",
                options={"temperature": 0},
            )
            text = (r.message.content or "").strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
            result = json.loads(text)
            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object")
            return result
        except Exception as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(1.5)
    raise RuntimeError(f"LLM JSON call failed: {last_error}")


def extract_pages(pdf_path):
    pages = []
    with fitz.open(pdf_path) as pdf:
        for i, page in enumerate(pdf):
            text = page.get_text("text", sort=True).strip()
            pages.append(
                {"page_number": i + 1, "text": text, "character_count": len(text)}
            )
    return pages


def metadata_extract(pages, pdf_name):
    # Use the opening pages for identity, and all-page text for a compact
    # supplementary search of metadata-like lines so the extraction is not
    # limited to the first page when the title block is unusual.
    opening = "\n\n".join(f"[PAGE {p['page_number']}]\n{p['text']}" for p in pages[:6])[
        :30000
    ]
    prompt = f"""
Extract structured metadata for the MAIN judgment in this PDF.
Return ONLY a JSON object matching this schema exactly. Use null for unknown
scalar values and [] for unknown lists. Preserve source wording in original
fields; normalize only the corresponding normalized fields.

{{
  "identification": {{
    "case_id": null,
    "case_title": null,
    "normalized_case_title": null,
    "case_number": null,
    "normalized_case_number": null,
    "neutral_citation": null,
    "reporter_citations": [],
    "decision_date": null,
    "document_type": null,
    "language": null
  }},
  "court_details": {{
    "court_name": null,
    "normalized_court_name": null,
    "court_level": null,
    "jurisdiction": null,
    "judges": [],
    "author_judge": null
  }},
  "parties": {{
    "appellants": [],
    "respondents": [],
    "other_parties": []
  }},
  "proceedings": {{
    "case_type": null,
    "originating_case_numbers": [],
    "connected_cases": [],
    "procedural_history": []
  }},
  "legal_context": {{
    "acts_and_statutes": [],
    "legal_provisions": [],
    "subject_tags": [],
    "legal_issues": [],
    "headnote": null,
    "keywords": []
  }},
  "case_analysis": {{
    "case_summary": null,
    "material_facts": [],
    "arguments_appellant": [],
    "arguments_respondent": [],
    "court_findings": [],
    "legal_principles": [],
    "decision_reasoning": [],
    "distinguishing_factors": []
  }},
  "outcome": {{
    "disposition": null,
    "final_order": null,
    "relief_granted": [],
    "directions_issued": []
  }},
  "provenance": {{
    "source_pdf": {json.dumps(pdf_name)},
    "page_count": {len(pages)},
    "field_evidence": {{}},
    "review_status": "pending"
  }}
}}

Rules:
- Use only the supplied judgment text. Never invent facts or fill gaps from memory.
- This is the judgment being processed, not any case cited within it.
- Keep original case titles, case numbers, citations, statute names, and provision
  references as printed. Normalized fields should be conservative lookup forms.
- reporter_citations includes reporter/parallel citations exactly as printed;
  neutral_citation is only the neutral citation if present.
- Judges should be names supported by the text; author_judge is the author if stated.
- Separate parties by procedural role in THIS appeal. Do not confuse counsel with parties.
- Keep facts, arguments, findings, principles, reasoning, and final directions distinct.
- procedural_history and connected_cases should contain concise, source-grounded entries.
- field_evidence maps important JSON paths to short verbatim quotes and page numbers,
  e.g. "identification.case_title": {{"page_number": 1, "quote": "..."}}
- If a field is unsupported, use null or [] and do not add an evidence quote.
- No markdown or explanation outside JSON.

SOURCE:
{opening}
"""
    result = ask_json(
        "You are a cautious Indian legal judgment metadata extractor. "
        "Return only valid JSON, use only supplied source text, and do not infer absent facts.",
        prompt,
    )
    # Ensure the schema remains stable even if the model omits an empty field.
    schema = {
        "identification": {
            "case_id": None,
            "case_title": None,
            "normalized_case_title": None,
            "case_number": None,
            "normalized_case_number": None,
            "neutral_citation": None,
            "reporter_citations": [],
            "decision_date": None,
            "document_type": None,
            "language": None,
        },
        "court_details": {
            "court_name": None,
            "normalized_court_name": None,
            "court_level": None,
            "jurisdiction": None,
            "judges": [],
            "author_judge": None,
        },
        "parties": {"appellants": [], "respondents": [], "other_parties": []},
        "proceedings": {
            "case_type": None,
            "originating_case_numbers": [],
            "connected_cases": [],
            "procedural_history": [],
        },
        "legal_context": {
            "acts_and_statutes": [],
            "legal_provisions": [],
            "subject_tags": [],
            "legal_issues": [],
            "headnote": None,
            "keywords": [],
        },
        "case_analysis": {
            "case_summary": None,
            "material_facts": [],
            "arguments_appellant": [],
            "arguments_respondent": [],
            "court_findings": [],
            "legal_principles": [],
            "decision_reasoning": [],
            "distinguishing_factors": [],
        },
        "outcome": {
            "disposition": None,
            "final_order": None,
            "relief_granted": [],
            "directions_issued": [],
        },
        "provenance": {
            "source_pdf": pdf_name,
            "page_count": len(pages),
            "field_evidence": {},
            "review_status": "pending",
        },
    }

    def fill_missing(target, defaults):
        for key, default in defaults.items():
            if (
                key not in target
                or target[key] is None
                and isinstance(default, (dict, list))
            ):
                target[key] = (
                    default.copy() if isinstance(default, (dict, list)) else default
                )
            elif isinstance(default, dict) and isinstance(target.get(key), dict):
                fill_missing(target[key], default)

    fill_missing(result, schema)
    result["provenance"]["source_pdf"] = pdf_name
    result["provenance"]["page_count"] = len(pages)
    return result


# Candidate patterns help recall; they are not a complete citation grammar.
PATTERNS = [
    re.compile(r"\b(?:\[\d{4}\]\s*)?\d+\s+SCR\s+\d+\b", re.I),
    re.compile(r"\bAIR\s+\d{4}\s+(?:SC|Del|Bom|Mad|Cal|All|Ker)\s+\d+\b", re.I),
    re.compile(r"\b\d{4}\s+INSC\s+\d+\b", re.I),
    re.compile(
        r"\b\d{4}\s+SCC\s+OnLine\s+(?:SC|Del|Bom|Mad|Cal|All|Ker)\s+\d+\b", re.I
    ),
    re.compile(r"\b\d{4}\s+OnLine\s+(?:SC|Del|Bom|Mad|Cal|All|Ker|Raj)\s+\d+\b", re.I),
    re.compile(r"\b(?:\(\d{4}\)\s*)?\d+\s+SCC(?:\s*\(Cri\))?\s+\d+\b", re.I),
]


def candidates_for_page(page):
    text, out = page["text"], []
    for pattern in PATTERNS:
        for m in pattern.finditer(text):
            a, b = m.span()
            out.append(
                {
                    "raw_candidate": m.group(0),
                    "page_number": page["page_number"],
                    "context": text[max(0, a - 220) : min(len(text), b + 220)].strip(),
                }
            )
    unique = {}
    for x in out:
        unique[(x["page_number"], x["raw_candidate"].lower(), x["context"])] = x
    return list(unique.values())


def batches(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def citations_extract(pages):
    all_records, seen = [], set()
    page_batches = list(batches(pages, PAGE_BATCH_SIZE))
    system = (
        "You extract case citations from Indian court judgments. Use only the "
        "supplied text. Never invent case names/citations. Preserve raw citation "
        "strings. Do not infer treatment from a mere citation list. Return JSON."
    )
    for n, group in enumerate(page_batches, 1):
        text = "\n\n".join(f"[PAGE {p['page_number']}]\n{p['text']}" for p in group)
        cand = []
        for p in group:
            cand.extend(candidates_for_page(p))
        prompt = f"""
Extract references to other cases in this text batch. Inspect the text itself;
the regex candidates are only hints and may miss citations or include false hits.
Return JSON:
{{
 "citations": [
  {{
   "cited_reference_text": null,
   "extracted_case_title": null,
   "extracted_citations": [],
   "context": null,
   "source_page": null,
   "paragraph_or_section": null,
   "reference_type": "case_citation",
   "treatment": "not_stated",
   "matched_case_id": null,
   "match_method": null,
   "verification_status": "pending",
   "evidence_text": null,
   "extraction_confidence": "low"
  }}
 ]
}}
Allowed treatment: followed, distinguished, overruled, reversed, approved,
referred_to, relied_on, held_inapplicable, not_stated, other.
One record per cited case occurrence or clearly grouped entry. Keep every raw
citation string. page_number must match a [PAGE N] marker. evidence_text must be
verbatim. If treatment is not explicit, use not_stated. Editorial "Case Law
Cited" lists must not be assumed to represent the court's own treatment.
Regex candidates:
{json.dumps(cand, ensure_ascii=False)[:10000]}
SOURCE TEXT:
{text[:30000]}
"""
        result = ask_json(system, prompt)
        records = result.get("citations", [])
        if not isinstance(records, list):
            records = []
        for c in records:
            if not isinstance(c, dict):
                continue
            # Backward-compatible aliases are folded into the agreed output schema.
            if "extracted_case_title" not in c:
                c["extracted_case_title"] = c.get("cited_case_title")
            if "extracted_citations" not in c:
                c["extracted_citations"] = c.get("raw_citations", [])
            if "source_page" not in c:
                c["source_page"] = c.get("page_number")
            if "cited_reference_text" not in c:
                c["cited_reference_text"] = c.get("evidence_text")
            for key, default in {
                "cited_reference_text": None,
                "extracted_case_title": None,
                "extracted_citations": [],
                "context": None,
                "source_page": None,
                "paragraph_or_section": None,
                "reference_type": "case_citation",
                "treatment": "not_stated",
                "matched_case_id": None,
                "match_method": None,
                "verification_status": "pending",
                "evidence_text": None,
                "extraction_confidence": "low",
            }.items():
                c.setdefault(key, default)
            key = (
                str(c.get("extracted_case_title") or "").lower(),
                tuple(sorted(map(str, c.get("extracted_citations") or []))),
                str(c.get("source_page")),
                str(c.get("evidence_text") or "").lower(),
            )
            if key not in seen:
                seen.add(key)
                all_records.append(c)
        print(f"Citation batches: {n}/{len(page_batches)}; records: {len(all_records)}")
    return all_records


def judge_metadata(metadata, pages):
    source = "\n\n".join(f"[PAGE {p['page_number']}]\n{p['text']}" for p in pages[:5])[
        :24000
    ]
    prompt = f"""
Audit the proposed metadata against source text. Return JSON:
{{
 "overall_status": "pass | needs_review | fail",
 "field_checks": [
  {{"field":"case_title","status":"supported | unsupported | uncertain",
    "evidence":null,"reason":null}}
 ],
 "missing_or_suspicious_fields": []
}}
Check identification.case_title, identification.decision_date,
identification.case_number, court_details.judges,
identification.neutral_citation, identification.reporter_citations,
and parties. Do not use outside knowledge.
PROPOSED METADATA:
{json.dumps(metadata, ensure_ascii=False)}
SOURCE:
{source}
"""
    return ask_json(
        "You are a strict legal extraction auditor. Only source evidence counts.",
        prompt,
    )


def judge_citations(records, pages):
    reports = []
    for start in range(0, len(records), 8):
        group = records[start : start + 8]
        nums = sorted(
            {
                int(c["page_number"])
                for c in group
                if str(c.get("page_number", "")).isdigit()
                and 1 <= int(c["page_number"]) <= len(pages)
            }
        )
        source = "\n\n".join(f"[PAGE {n}]\n{pages[n-1]['text']}" for n in nums)
        if not source:
            source = "\n\n".join(
                f"[PAGE {p['page_number']}]\n{p['text']}" for p in pages[:3]
            )
        prompt = f"""
Audit proposed citation records against source text. Return JSON:
{{
 "citation_checks": [
  {{
   "record_index": 0,
   "status": "supported | unsupported | uncertain",
   "case_name_supported": "supported | unsupported | uncertain",
   "raw_citation_supported": "supported | unsupported | uncertain",
   "treatment_supported": "supported | unsupported | uncertain",
   "page_supported": "supported | unsupported | uncertain",
   "evidence": null,
   "reason": null
  }}
 ]
}}
record_index is zero-based within this batch. A citation is supported only if
present in the text. Treatment requires explicit textual evidence. Do not infer
that an editorial citation list means the court followed or relied on a case.
PROPOSED RECORDS:
{json.dumps(group, ensure_ascii=False)}
SOURCE TEXT:
{source[:26000]}
"""
        reports.append(
            {
                "start_index": start,
                "report": ask_json(
                    "You are a strict legal citation auditor. Return JSON only.", prompt
                ),
            }
        )
    return {"batches": reports}


def run(pdf_path):
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    outdir = pdf_path.parent / f"{pdf_path.stem}_extracted"
    outdir.mkdir(parents=True, exist_ok=True)

    print("[1/5] Extracting PDF text...")
    pages = extract_pages(pdf_path)
    total_chars = sum(p["character_count"] for p in pages)
    low_text_pages = [p["page_number"] for p in pages if p["character_count"] < 30]
    text_report = {
        "page_count": len(pages),
        "total_characters": total_chars,
        "pages_with_little_text": low_text_pages,
        "ocr_may_be_needed": total_chars < 500
        or len(low_text_pages) > len(pages) * 0.4,
    }
    save_json(outdir / "pages.json", pages)
    (outdir / "full_text.txt").write_text(
        "\n\n".join(f"[PAGE {p['page_number']}]\n{p['text']}" for p in pages),
        encoding="utf-8",
    )
    save_json(outdir / "text_extraction_report.json", text_report)
    print(f"      {len(pages)} pages, {total_chars} extracted characters")
    if text_report["ocr_may_be_needed"]:
        print("WARNING: text extraction looks sparse; scanned pages may need OCR.")

    print("[2/5] Extracting judgment metadata...")
    metadata = metadata_extract(pages, pdf_path.name)
    save_json(outdir / "judgment_metadata.json", metadata)

    print("[3/5] Finding regex citation candidates...")
    regex_candidates = [c for p in pages for c in candidates_for_page(p)]
    save_json(outdir / "citation_candidates.json", regex_candidates)
    print(f"      {len(regex_candidates)} candidates")

    print("[4/5] Extracting citation records...")
    citations = citations_extract(pages)
    save_json(outdir / "citations.json", {"citations": citations})
    print(f"      {len(citations)} citation records")

    print("[5/5] LLM-as-judge review...")
    report = {
        "metadata_judgment": judge_metadata(metadata, pages),
        "citations_judgment": judge_citations(citations, pages),
        "text_extraction_report": text_report,
        "warning": "LLM review is not proof. Manually audit a sample and all uncertain records.",
    }
    save_json(outdir / "validation_report.json", report)
    print(f"Done. Outputs: {outdir}")
    for name in [
        "full_text.txt",
        "pages.json",
        "text_extraction_report.json",
        "judgment_metadata.json",
        "citation_candidates.json",
        "citations.json",
        "validation_report.json",
    ]:
        print(" -", name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Path to one judgment PDF")
    args = parser.parse_args()
    run(Path(args.pdf).resolve())
