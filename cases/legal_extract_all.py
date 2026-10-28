"""
legal_extract_all.py
Extract page-wise text, judgment metadata, cited cases, and an LLM-as-judge
review from one judgment PDF using a local Ollama OpenAI-compatible endpoint.

Install:
    python -m pip install pymupdf openai

Run PowerShell:
    $env:LLM_MODEL="your-exact-model-tag-from-ollama-list"
    python legal_extract_all.py "C:\path\to\judgment.pdf"

Outputs are saved beside the PDF in <pdf_name>_extracted/.
LLM review is not proof of correctness; manually verify legal extractions.
"""

import os, re, json, time, argparse
from pathlib import Path
import fitz
from openai import OpenAI

BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv("LLM_MODEL", "REPLACE_WITH_OLLAMA_MODEL_TAG")
client = OpenAI(
    base_url=BASE_URL, api_key=os.getenv("LLM_API_KEY", "ollama"), timeout=180.0
)
RETRIES = 2
PAGE_BATCH_SIZE = int(os.getenv("PAGE_BATCH_SIZE", "4"))


def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def ask_json(system, prompt):
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            r = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            text = (r.choices[0].message.content or "").strip()
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
    opening = "\n\n".join(f"[PAGE {p['page_number']}]\n{p['text']}" for p in pages[:5])[
        :24000
    ]
    prompt = f"""
Extract metadata for the main judgment at the start of this source text.
Return ONLY JSON with this schema:
{{
 "case_title": null,
 "court": "Supreme Court of India",
 "decision_date": null,
 "case_number": null,
 "bench": [],
 "neutral_citation": null,
 "parallel_citations": [],
 "petitioner_names": [],
 "respondent_names": [],
 "acts_and_sections": [],
 "source_pdf": {json.dumps(pdf_name)},
 "evidence": {{
   "case_title": null, "decision_date": null, "case_number": null,
   "bench": null, "neutral_citation": null
 }},
 "review_status": "pending"
}}
Rules: Use only the source. Never invent missing data. Use null or [] when absent.
Keep citation strings exactly as printed. Decision date is not the same as a
reporter citation year. For each important field, evidence should be a short
verbatim quote or null. Do not extract metadata for cited cases.
SOURCE:
{opening}
"""
    result = ask_json(
        "You are a cautious Indian legal-document metadata extractor. "
        "Use only supplied text; do not infer absent facts. Return valid JSON.",
        prompt,
    )
    defaults = {
        "case_title": None,
        "court": None,
        "decision_date": None,
        "case_number": None,
        "bench": [],
        "neutral_citation": None,
        "parallel_citations": [],
        "petitioner_names": [],
        "respondent_names": [],
        "acts_and_sections": [],
        "source_pdf": pdf_name,
        "evidence": {},
        "review_status": "pending",
    }
    for k, v in defaults.items():
        result.setdefault(k, v)
    result["source_pdf"] = pdf_name
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
   "cited_case_title": null,
   "raw_citations": [],
   "reporter": null,
   "citation_year": null,
   "treatment": "not_stated",
   "context": null,
   "page_number": null,
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
            for key, default in {
                "cited_case_title": None,
                "raw_citations": [],
                "reporter": None,
                "citation_year": None,
                "treatment": "not_stated",
                "context": None,
                "page_number": None,
                "evidence_text": None,
                "extraction_confidence": "low",
            }.items():
                c.setdefault(key, default)
            key = (
                str(c.get("cited_case_title") or "").lower(),
                tuple(sorted(map(str, c.get("raw_citations") or []))),
                str(c.get("page_number")),
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
Check case_title, decision_date, case_number, bench, neutral_citation,
parallel_citations and party names. Do not use outside knowledge.
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
    if MODEL == "REPLACE_WITH_OLLAMA_MODEL_TAG":
        raise ValueError("Set LLM_MODEL to the exact model tag shown by `ollama list`.")
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
