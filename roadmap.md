Based on the three phases in your proposed methodology, we are currently at Phase 1: Data and Statutory Graph, specifically the corpus preparation and case identity metadata extraction substage.

We have not yet completed Phase 1.

## Where we stand

Phase 1 — Data and Statutory Graph

In progress

1. Corpus identification and metadata extraction

   Current task
   - Identify each judgment and its PDF.
   - Extract case title, aliases, citations, case numbers, date, bench and other identity metadata.
   - Build a reliable mapping between citation variants and `case_id`.
2. Paragraph-level corpus construction

   Not started
   - Extract judgment text paragraph-wise.
   - Assign `opinion_id` and `para_id`.
   - Preserve separate numbering for concurring and dissenting opinions.
   - Record paragraph source version.
3. Citation extraction and resolution

   Not started
   - Extract citation strings using rules.
   - Resolve citations to corpus `case_id`.
   - Parse pinpoint references.
4. Statutory graph construction

   Not started
   - Build IPC/BNS, CrPC/BNSS and IEA/BSA provision mappings.
   - Add multi-label edges.
   - Obtain independent expert annotations and agreement scores.
5. Dataset splits and leakage checks

   Not started
   - Train/dev: 2015–2023.
   - Test: 2025–2026.
   - Ensure no `case_id` overlap.

Phase 2 — Benchmark InCite-IN: Not started

Phase 3 — Verifier and Repair: Not started

## What have we actually completed?

| Work                                            | Status                     |
| ----------------------------------------------- | -------------------------- |
| Examined three sample judgments                 | Completed                  |
| Identified different case citation/name formats | Initial analysis completed |
| Designed Level 1 metadata schema                | Initial version created    |
| Reduced metadata extraction script              | Created                    |
| Tested extraction on all three PDFs             | Pending                    |
| Validated LLM-as-judge results                  | Pending                    |
| Finalized metadata schema                       | Pending                    |

## Our immediate next step

Run and validate `legal_metadata_extractor.py` on the three sample judgments.

After that, we should freeze the case identity metadata schema and move to paragraph-level corpus construction.

One important distinction: the metadata extractor we created is only the first component of Phase 1. It does not yet implement the full corpus schema in your methodology (`case_id`, `date`, `bench`, `opinion_id`, `para_id`, `text`, source version).

So our current position is:

Phase 1 → Corpus preparation → Judgment identity and metadata extraction.

We should finish this substage before implementing paragraph extraction.