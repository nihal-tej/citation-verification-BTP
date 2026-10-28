"""
build_multi_dataset.py
──────────────────────
Builds a unified patient-simulation dataset by merging three sources:

  Source 1 — GBaker/MedQA-USMLE-4-options   (USMLE, US exam)
  Source 2 — openlifescienceai/medmcqa       (AIIMS/NEET, Indian PG exam)
  Source 3 — shzyk/DiagnosisArena            (real journal clinical cases)

Verified dataset facts
──────────────────────
MedQA        : train 10,178 | test 1,273
               columns: question, answer, options (dict), meta_info, answer_idx
               ~40–50% patient vignettes after filter  → ~4,000–6,000 (train), ~500 (test)

MedMCQA      : train 182,822 | validation 4,183 | test 6,150
               columns: question, opa, opb, opc, opd, cop (int 0–3), choice_type, exp, subject_name
               cop is an integer class label (0→A, 1→B, 2→C, 3→D)
               ~10–15% patient vignettes — use text filter + choice_type=="single"
               → ~300–500 (validation), ~15,000–25,000 (train)

DiagnosisArena: test 915 (single split)
               columns: id, "Case Information", "Physical Examination",
                        "Diagnostic Tests", "Final Diagnosis", Options (dict), "Right Option"
               100% patient cases from real journals → no content filter needed
               Harder cases; rare diagnoses; good for stress-testing the framework

Combined eval target (test/validation splits only):
  MedQA test       ~500
  MedMCQA val      ~400
  DiagnosisArena   ~900
  ─────────────────────
  Total            ~1,800 cases

Usage
─────
  python build_multi_dataset.py               # default: eval splits
  MODE=train python build_multi_dataset.py    # training splits (much larger)
"""

import os
import json
import asyncio
from typing import Optional
from datasets import load_dataset
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import UserMessage, SystemMessage

# ── CONFIG ─────────────────────────────────────────────────────────────────────
LLM_BASE_URL  = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL     = os.getenv("LLM_MODEL",    "qwen3.6:35b")
DUMMY_API_KEY = "ollama"

# MODE="eval" uses test/validation splits; MODE="train" uses train splits.
MODE = os.getenv("MODE", "eval")

OUTPUT_FILE     = f"cases_{MODE}.json"
CHECKPOINT_FILE = f"checkpoint_{MODE}.json"
CHECKPOINT_EVERY = 20

LLM_MAX_RETRIES = 2
LLM_RETRY_DELAY = 1.5

# Per-source caps (set to None for no cap)
SOURCE_CAPS = {
    "medqa":          int(os.getenv("CAP_MEDQA",          500   if MODE == "eval" else 5000)),
    "medmcqa":        int(os.getenv("CAP_MEDMCQA",        500   if MODE == "eval" else 10000)),
    "diagnosisarena": int(os.getenv("CAP_DIAGNOSISARENA", 915)),  # all of it
}

# ── SHARED FILTERS ─────────────────────────────────────────────────────────────
DIAGNOSIS_PHRASES = [
    "most likely diagnosis",
    "most likely cause",
    "most likely etiology",
    "most likely underlying cause",
    "most likely pathogenesis",
    "most likely pathophysiology",
    "most likely responsible",
    "most likely to be caused",
    "most likely finding",
]
MANAGEMENT_PHRASES = [
    "best next step",
    "most appropriate next step",
    "next best step",
    "best next step in management",
    "most appropriate step in management",
    "most appropriate management",
    "best course of action",
    "best course of treatment",
    "most appropriate treatment",
    "most appropriate initial",
    "most appropriate pharmacotherapy",
]

# Non-patient scenarios: researcher bench experiments, autopsies
EXCLUDE_PREFIXES = (
    "an investigator",
    "a researcher",
    "an autopsy",
    "a pulmonary autopsy",
)

# Integer → letter for MedMCQA's cop field
COP_TO_LETTER = {0: "A", 1: "B", 2: "C", 3: "D"}


def classify_question(question_lower: str) -> Optional[str]:
    """Return 'diagnosis', 'management', or None (skip)."""
    if any(p in question_lower for p in DIAGNOSIS_PHRASES):
        return "diagnosis"
    if any(p in question_lower for p in MANAGEMENT_PHRASES):
        return "management"
    return None


def is_patient_scenario(question_lower: str) -> bool:
    """False for lab experiments and autopsies."""
    return not question_lower.startswith(EXCLUDE_PREFIXES)


# ── LLM CLIENT ─────────────────────────────────────────────────────────────────
def make_client() -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=LLM_MODEL,
        api_key=DUMMY_API_KEY,
        base_url=LLM_BASE_URL,
        temperature=0.0,
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": False,
        },
    )


async def extract_chief_complaint(
    client: OpenAIChatCompletionClient,
    vignette: str,
    retries: int = LLM_MAX_RETRIES,
) -> str:
    """
    Sole LLM job: extract chief complaint from the vignette in first-person.
    Raises RuntimeError after all retries are exhausted.
    """
    prompt = (
        "You are a clinical assistant. Read the clinical vignette below.\n"
        "Write ONE sentence from the patient's first-person perspective describing why they are seeking care.\n"
        "Example: \"I've had crushing chest pain radiating to my left arm for the past hour.\"\n\n"
        "Rules:\n"
        "- One sentence only.\n"
        "- First-person (I / my / me).\n"
        "- Capture the chief symptom and duration if stated.\n"
        "- Do NOT include diagnostic labels or lab values.\n"
        "- Output ONLY valid JSON: {\"chief_complaint\": \"...\"}\n\n"
        f"Vignette:\n{vignette}"
    )

    for attempt in range(retries + 1):
        try:
            response = await client.create(
                messages=[
                    SystemMessage(
                        content="You output ONLY valid JSON — no markdown, no preamble.",
                        source="system",
                    ),
                    UserMessage(content=prompt, source="user"),
                ],
                extra_create_args={"response_format": {"type": "json_object"}},
            )
            content = response.content.strip()
            content = (
                content
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            return json.loads(content)["chief_complaint"]
        except Exception as exc:
            if attempt == retries:
                raise RuntimeError(
                    f"LLM failed after {retries + 1} attempts: {exc}"
                ) from exc
            await asyncio.sleep(LLM_RETRY_DELAY)


# ── SOURCE ADAPTERS ─────────────────────────────────────────────────────────────
# Each adapter receives a raw dataset row and returns either a normalized dict
# (ready for CC extraction) or None (skip this row).
# The dict must contain: vignette_for_cc, hidden_vignette, options, answer_idx,
# answer_text, question_type, and any source-specific extras.

def adapt_medqa(row: dict) -> Optional[dict]:
    """Normalize a MedQA row. Returns None if the row should be skipped."""
    question = row["question"]
    q_lower  = question.lower()

    question_type = classify_question(q_lower)
    if question_type is None:
        return None
    if not is_patient_scenario(q_lower):
        return None

    return {
        "vignette_for_cc": question,        # text fed to LLM for CC extraction
        "hidden_vignette":  question,
        "options":          row["options"],  # already {"A": ..., "B": ..., ...}
        "answer_idx":       row["answer_idx"],
        "answer_text":      row["answer"],
        "question_type":    question_type,
        "meta_info":        row["meta_info"],
        "subject":          None,
        "explanation":      None,
    }


def adapt_medmcqa(row: dict) -> Optional[dict]:
    """
    Normalize a MedMCQA row.

    MedMCQA schema:
      question, opa, opb, opc, opd  — options as separate columns
      cop                           — int (0–3) class label for correct option
      choice_type                   — "single" | "multi"
      exp                           — explanation text (may be None)
      subject_name                  — one of 21 medical subjects
    """
    # Skip multi-correct questions (inconsistent format for simulation)
    if row.get("choice_type") == "multi":
        return None

    question = row["question"]
    q_lower  = question.lower()

    question_type = classify_question(q_lower)
    if question_type is None:
        return None
    if not is_patient_scenario(q_lower):
        return None

    # Normalize options into the same dict format as MedQA
    options = {
        "A": str(row["opa"]),
        "B": str(row["opb"]),
        "C": str(row["opc"]),
        "D": str(row["opd"]),
    }

    # cop is an integer class label: 0→A, 1→B, 2→C, 3→D
    cop_raw = row["cop"]
    try:
        cop_int = int(cop_raw)
    except (ValueError, TypeError):
        return None                        # malformed row, skip
    if cop_int not in COP_TO_LETTER:
        return None
    answer_idx  = COP_TO_LETTER[cop_int]
    answer_text = options[answer_idx]

    return {
        "vignette_for_cc": question,
        "hidden_vignette":  question,
        "options":          options,
        "answer_idx":       answer_idx,
        "answer_text":      answer_text,
        "question_type":    question_type,
        "meta_info":        None,
        "subject":          row.get("subject_name"),
        "explanation":      row.get("exp"),  # explanation of correct answer
    }


def adapt_diagnosisarena(row: dict) -> Optional[dict]:
    """
    Normalize a DiagnosisArena row.

    DiagnosisArena schema:
      id                  — int
      "Case Information"  — initial patient presentation (ideal for CC)
      "Physical Examination"
      "Diagnostic Tests"
      "Final Diagnosis"
      Options             — dict {"A": ..., "B": ..., "C": ..., "D": ...}
      "Right Option"      — letter "A" | "B" | "C" | "D"
    """
    # All DiagnosisArena rows are already diagnosis cases — no text filter needed.
    case_info   = row.get("Case Information", "")
    phys_exam   = row.get("Physical Examination", "")
    diag_tests  = row.get("Diagnostic Tests", "")

    # Combine all three sections for the hidden vignette (evaluator sees everything)
    hidden_vignette = (
        f"Case Information:\n{case_info}\n\n"
        f"Physical Examination:\n{phys_exam}\n\n"
        f"Diagnostic Tests:\n{diag_tests}"
    ).strip()

    # Use only Case Information for CC extraction (initial presentation, no exam/tests)
    vignette_for_cc = case_info.strip()

    if not vignette_for_cc:
        return None

    options    = row.get("Options", {})
    answer_idx = row.get("Right Option", "").strip()
    if answer_idx not in ("A", "B", "C", "D"):
        return None
    answer_text = options.get(answer_idx, "")

    return {
        "vignette_for_cc": vignette_for_cc,
        "hidden_vignette":  hidden_vignette,
        "options":          options,
        "answer_idx":       answer_idx,
        "answer_text":      answer_text,
        "question_type":    "diagnosis",  # DiagnosisArena is exclusively diagnosis
        "meta_info":        None,
        "subject":          None,
        "explanation":      None,
    }


# ── SOURCE CONFIGS ──────────────────────────────────────────────────────────────
# Each entry: (hf_dataset_name, split_name, adapter_fn, source_tag)
SOURCE_CONFIGS = [
    (
        "GBaker/MedQA-USMLE-4-options",
        "test" if MODE == "eval" else "train",
        adapt_medqa,
        "medqa",
    ),
    (
        "openlifescienceai/medmcqa",
        "validation" if MODE == "eval" else "train",
        adapt_medmcqa,
        "medmcqa",
    ),
    (
        "shzyk/DiagnosisArena",
        "test",                     # only split available
        adapt_diagnosisarena,
        "diagnosisarena",
    ),
]


# ── CHECKPOINT ─────────────────────────────────────────────────────────────────
def load_checkpoint() -> tuple[list[dict], dict[str, set[int]]]:
    """
    Returns (cases, processed) where processed is a dict mapping
    source_tag → set of already-processed row indices.
    """
    if not os.path.exists(CHECKPOINT_FILE):
        return [], {}
    with open(CHECKPOINT_FILE) as f:
        ckpt = json.load(f)
    cases     = ckpt.get("cases", [])
    processed = {k: set(v) for k, v in ckpt.get("processed", {}).items()}
    print(f"  ↩  Resumed: {len(cases)} cases already saved.\n")
    return cases, processed


def save_checkpoint(cases: list[dict], processed: dict[str, set[int]]) -> None:
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(
            {
                "cases":     cases,
                "processed": {k: list(v) for k, v in processed.items()},
            },
            f,
            indent=2,
        )


# ── MAIN ───────────────────────────────────────────────────────────────────────
async def process_source(
    client:     OpenAIChatCompletionClient,
    hf_name:    str,
    split:      str,
    adapter_fn,
    source_tag: str,
    cap:        int,
    cases:      list[dict],
    processed:  dict[str, set[int]],
) -> dict:
    """Process one source dataset. Appends to `cases` in-place. Returns stats."""
    print(f"\n{'─'*60}")
    print(f"  Source : {source_tag}")
    print(f"  Dataset: {hf_name}  split={split}")
    print(f"  Cap    : {cap}")
    print(f"{'─'*60}")

    dataset = load_dataset(hf_name, split=split)
    print(f"  Rows loaded: {len(dataset)}")

    already_done = processed.get(source_tag, set())
    if source_tag not in processed:
        processed[source_tag] = set()

    case_count  = sum(1 for c in cases if c["source"] == source_tag)
    stats       = {"filter": 0, "patient": 0, "llm_err": 0, "done": len(already_done)}

    for row_idx, row in enumerate(dataset):
        if case_count >= cap:
            break
        if row_idx in already_done:
            continue

        # ── Adapter: normalize schema + apply filters ─────────────────────────
        normalized = adapter_fn(row)
        if normalized is None:
            stats["filter"] += 1
            continue

        # ── LLM: extract chief complaint ──────────────────────────────────────
        try:
            chief_complaint = await extract_chief_complaint(
                client, normalized["vignette_for_cc"]
            )
        except RuntimeError as exc:
            print(f"    ⚠  Row {row_idx}: {exc}")
            stats["llm_err"] += 1
            processed[source_tag].add(row_idx)
            continue

        # ── Assemble final case ───────────────────────────────────────────────
        case_count += 1
        case = {
            "case_id":                 f"{source_tag}_case_{case_count}",
            "source":                  source_tag,
            "question_type":           normalized["question_type"],
            "meta_info":               normalized["meta_info"],
            "subject":                 normalized["subject"],
            "chief_complaint":         chief_complaint,
            "hidden_vignette":         normalized["hidden_vignette"],
            "options":                 normalized["options"],
            "ground_truth_answer_idx": normalized["answer_idx"],
            "ground_truth_answer":     normalized["answer_text"],
            "explanation":             normalized["explanation"],
        }
        cases.append(case)
        processed[source_tag].add(row_idx)

        print(
            f"    [{case_count:>5}/{cap}]"
            f"  ({normalized['question_type']:<11})"
            f"  {normalized['answer_text'][:60]}"
        )

        if len(cases) % CHECKPOINT_EVERY == 0:
            save_checkpoint(cases, processed)

    return stats


async def build_dataset() -> None:
    print(f"\n{'═'*60}")
    print(f"  Multi-source medical dataset builder")
    print(f"  MODE  : {MODE}")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"{'═'*60}")

    cases, processed = load_checkpoint()
    client           = make_client()
    all_stats        = {}

    for hf_name, split, adapter_fn, source_tag in SOURCE_CONFIGS:
        cap = SOURCE_CAPS[source_tag]
        stats = await process_source(
            client, hf_name, split, adapter_fn,
            source_tag, cap, cases, processed,
        )
        all_stats[source_tag] = stats

    # ── Final save ────────────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "w") as f:
        json.dump(cases, f, indent=4)

    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    # ── Summary ───────────────────────────────────────────────────────────────
    def count(field, value):
        return sum(1 for c in cases if c.get(field) == value)

    print(f"\n{'═'*60}")
    print(f"  ✅  Saved {len(cases)} cases → {OUTPUT_FILE}")
    print(f"{'═'*60}")
    print(f"\n  By source:")
    for tag in ("medqa", "medmcqa", "diagnosisarena"):
        n = sum(1 for c in cases if c["source"] == tag)
        s = all_stats.get(tag, {})
        print(
            f"    {tag:<18} {n:>5} cases"
            f"  (skipped: filter={s.get('filter',0)}"
            f"  llm_err={s.get('llm_err',0)})"
        )
    print(f"\n  By question type:")
    print(f"    diagnosis   {count('question_type', 'diagnosis'):>5}")
    print(f"    management  {count('question_type', 'management'):>5}")
    print(f"\n  By meta_info:")
    print(f"    step1       {count('meta_info', 'step1'):>5}")
    print(f"    step2&3     {count('meta_info', 'step2&3'):>5}")
    print(f"    (none)      {sum(1 for c in cases if c['meta_info'] is None):>5}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    asyncio.run(build_dataset())