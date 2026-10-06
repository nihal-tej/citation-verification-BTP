# RhetoriCite-India v2: Revised Implementation Plan

**Core claim (one sentence):** Rhetorical role is the missing variable in citation-support verification: citations that point to a real paragraph in the right case can still fail because the paragraph records an argument or fact, not the court's own holding. We test this on the first Indian Supreme Court pinpoint-citation benchmark.

**Contribution ranking:** (1) benchmark + the rhetorical-role finding; (2) role-aware verifier; (3) IPC/BNS-era statutory graph as a secondary, expert-validated resource. "Agentic recovery" is demoted to a repair module.

## 0. Hypotheses (pre-registered, directional)

| ID | Hypothesis | Falsified if |
| --- | --- | --- |
| H1 | Frontier LLMs with a page-grounded prompt miss a substantial share of Tier 3 (rhetorical trap) items | Recall on Tier 3 is already within 5 pp of Tier 1 |
| H2 | Feeding the verifier only role-filtered text raises precision at equal recall vs. full-paragraph input | A1 vs A0 differs by \< 2 pp F1 (paired test) |
| H3 | Abstention on high mutual-information items lowers error on answered items (risk-coverage curve beats no-abstain) | AURC not better than the max-prob baseline |
| H4 | Role tagger errors cap the hard-rule gate: oracle roles beat predicted roles by a measurable margin | Gap \< 2 pp (then tagger quality is not the bottleneck) |

Hypotheses replace the "expected result" language in v1. No target FPR is promised.

## 1. Cross-Check Register (v1 → v2)

| # | v1 item | Problem found | v2 resolution |
| --- | --- | --- | --- |
| 1 | "ISS dataset", 7 roles incl. "Other" | No dataset by that name found; label set matches no published schema | Use the Bhattacharya et al. 2019 schema (Facts, Ruling by Lower Court, Argument, Statute, Precedent, Ratio of the Decision, Ruling by Present Court). Train on LegalSeg and/or AILA/OpenNyAI data; cite exactly |
| 2 | "Ratio Decidendi" label | Dataset "Ratio" is not the doctrinal ratio decidendi | Rename `RATIO_ANALYSIS`; define `R_auth` explicitly in the paper |
| 3 | Precedent ∈ R_auth | Discussion of an earlier case is not the present court's holding | `PRE_RELIED` counts only when P restates a precedent; otherwise excluded |
| 4 | Rule 1 existential (∃ sentence in R_auth) | Mixed paragraphs pass; Tier 3 items leak through | Alignment-based gate (Section 5) |
| 5 | Rules 1 and 3 overlap | Rule 3 already runs on T_auth; ablation confounded | Ablations A1/A2/A3 separate input filtering from hard rule |
| 6 | `ClaimType(P)` | Unspecified module | Explicit 4-class classifier with its own eval |
| 7 | "Rhetorical Gate lowers FPR" | Extra gates can only add rejections | FPR hypothesis moved to calibrated entailment + abstention (H2, H3) |
| 8 | Entropy ablation "FPR increases" | Requiring H \< τ to pass makes the gate stricter; direction wrong | Entropy becomes an ABSTAIN route; evaluate with risk-coverage |
| 9 | Predictive entropy called "epistemic" | It is total uncertainty | Use mutual information (ensemble/MC) plus calibration (ECE, temperature scaling) |
| 10 | Tier 2/3 distractors chosen via roles | Benchmark favors the tagger (circular) | Independent selection + human confirmation + tagger-independent subset (Section 4) |
| 11 | Tier 4 gold from own graph | Circular; ignores savings clause | Expert-labelled; offence-date semantics; savings rule (Section 3) |
| 12 | Only IPC↔BNS | CrPC→BNSS and Evidence Act→BSA changed the same day | Include all three transitions |
| 13 | Overruled/distinguished precedents absent | Most common temporal failure in practice | Optional Tier 6 if time allows; otherwise stated as a limitation |
| 14 | 4 edge types, single-label | Merged/split sections; sections both modified and re-punished | Multi-label edges + many-to-many mapping |
| 15 | 1950–2024 vs "2015–2025 for clean numbering" | Inconsistent; old judgments lack numbered paragraphs | Test on 2025–2026 judgments; train on 2015–2023 with numbering QA |
| 16 | Valid citations assumed valid | Judges cite loosely; SCC/AIR/INSC numbering differ | Human audit of 300 valid items; drop disputed ones |
| 17 | n=250/tier, no splits, no stats | Wide CIs; threshold tuning leakage | n=300/tier, case-level temporal split, Wilson CIs, McNemar |
| 18 | Baselines GPT-4o, Claude 3.5, Gemini 2.5, LLaMA-3.3 | Dated; Verma already evaluates GPT-5.4 | Current-generation models + one open-weight |
| 19 | `legalcite-support-base` as main fine-tuned baseline | US-only DeBERTa model; weak strawman | Keep as domain-shift probe; add an in-domain cross-encoder |
| 20 | No role-aware LLM baseline | Cannot separate "information" from "architecture" | Add B5: LLM given role tags / told to identify the court's own reasoning first |
| 21 | CitaLaw as "static evaluator" | It benchmarks citation *generation* | Drop from verification comparison; cite as related |
| 22 | ">70% token saving" | True by construction vs. 50-page input | Compare against cited-page baseline for verification; full-document only for repair |
| 23 | Hit@1 vs single gold paragraph | Several paragraphs may validly support P | Annotate any-valid sets; report Hit@k on those |
| 24 | InLegalBERT embeddings for ranking | Not a sentence encoder | BM25 + fine-tuned bi-encoder + cross-encoder rerank |
| 25 | P → P′ rewriting | Alters the lawyer's claim | Flag and suggest only; rewriting evaluated for faithfulness, off by default |
| 26 | Contamination | LLMs may have seen SC judgments | Post-cutoff test set + memorization probe |

## 2. Phase 0: Pilot with Go/No-Go 

| Pilot | Method | Go threshold | If it fails |
| --- | --- | --- | --- |
| P1 Feasibility | Extract and resolve pinpointed citations from 2025–2026 SC judgments | ≥ 1,500 resolvable pinpointed citations | Widen to High Courts or drop pinpoint to paragraph-range |
| P2 Is Tier 3 hard? | 60 hand-built Tier 3 items; 2–3 frontier LLMs, base and +Gnd. | Recall at least 15 pp below Tier 1 | Reframe paper around Tier 4/5; H1 dropped |
| P3 Tagger quality | Predict roles on 50 annotated judgments; paragraph-level eval | Macro-F1 ≥ 0.75 on Ratio vs. Argument vs. Facts | Soft weighting instead of hard gate; invest in tagger |
| P4 Citation extraction | Manual check of 200 extracted citations | ≥ 95% correct case resolution, ≥ 90% correct paragraph | Fix regexes for SCC/AIR/INSC/SCC OnLine before scaling |
| P5 Annotators | Recruit ≥ 2 law-trained annotators; 50-item calibration | Cohen's κ ≥ 0.7 | Rewrite guidelines; rerun |

Decision memo at end of week 3.

## 3. Phase 1: Data and Statutory Graph 

**Corpus.** Supreme Court judgments, JSON per paragraph (`case_id, date, bench, opinion_id, para_id, text`). Concurring/dissenting opinions keep separate numbering. Record source version (SCR/SCC/INSC) for every paragraph. Splits:

- **Train/dev:** 2015–2023
- **Test:** 2025–2026 (post-cutoff for most LLMs)
- No `case_id` shared across splits

**Citation extraction.** Rule-based extraction of citation strings (SCC, AIR, SCC OnLine, INSC), resolution to corpus `case_id`, then pinpoint parsing ("para 25", "paras 30–32"). Keep only citations whose target is in the corpus. Report selection bias (cited-in-corpus cases skew toward frequently cited ones).

**Statutory graph.** Nodes: IPC/BNS, CrPC/BNSS, IEA/BSA provisions. Sources: official comparative tables as primary; HF datasets only as secondary. Edges are **multi-label**: `EXACT`, `MATERIAL_MOD`, `PUNISHMENT_ALTERED`, `REPEALED_NEW`, plus `MERGED`/`SPLIT`. Two experts label independently; adjudicate; report κ. Applicability rule encoded explicitly:

- `t` means **offence/event date** (not filing or citation date), stated per instance.
- If `t` \< 1 July 2024 the old code applies, and the old section is valid.
- Edges matter only when the new code governs, subject to savings provisions (expert-checked).

## 4. Phase 2: Benchmark InCite-IN 

1,500 valid + 1,500 corrupted (5 tiers × 300), balanced; same count in train-set builds.

| Tier | Corruption | Selection (independent of the verifier) | Validation |
| --- | --- | --- | --- |
| T1 | Wrong case, different legal area | Random case from a different subject-matter cluster | Auto + spot check |
| T2 | Wrong pinpoint, unrelated paragraph | Random paragraph from same judgment outside ±5 paragraphs | 100% by one annotator |
| T3 | Rhetorical trap | Same-issue paragraph where the court records a rejected argument; candidates proposed by the tagger **and** by keyword/embedding similarity, accepted only after human confirmation that the argument was rejected | 100% by two annotators |
| T4 | Same-role wrong-issue (Ratio on a different issue) | Ratio paragraph in the same judgment on a different issue; embedding similarity band (not too close, not too far) | 100% by two annotators |
| T5 | Temporal/statutory drift | Valid citation + `t` or statute swap per graph rules | Expert-labelled |

**Anti-circularity checks:**

- Report results on the subset where tagger and human agree **and** on the subset selected without the tagger.
- Release annotator guidelines, disagreement logs, κ.
- Contamination probe: sentence-completion test on test judgments; compare 2025–2026 vs. older LLM accuracy.
- Audit 300 "valid" items for citation looseness; remove contested ones.

## 5. Phase 3: Verifier 

**Modules**

1. **Role tagger:** sentence-level, with paragraph aggregation. Hierarchical BiLSTM-CRF vs. transformer-over-InLegalBERT; pick on dev.
2. **ClaimType(P):** `HOLDING | FACT | STATUTE_TEXT | PROCEDURAL`, own training set, own eval.
3. **Statute extractor:** NER + normalisation of section references to graph nodes.
4. **NLI scorer:** SUPPORTS / CONTRADICTS / UNSUPPORTED. In-domain cross-encoder trained on the training-split corruptions plus augmented legal NLI data; ensemble of 5 (or MC-dropout, K=10); temperature-scaled.

**Decision logic (replaces v1 rules)**

- `T_auth` = sentences labelled `RATIO_ANALYSIS` or `RPC` (+ `PRE_RELIED` when P restates a precedent), with a ±1-sentence context window to keep coreference.
- **Gate_R (alignment-based):** compute support probability by role group. If ClaimType = HOLDING and the best-supporting sentence is `ARG/FACT/RLC` while no `T_auth` sentence supports → `REJECT: RHETORICAL_MISMATCH`.
- **Gate_S:** `p(SUPPORTS | P, T_auth) > τ_conf` → else `REJECT: LOW_ENTAILMENT`.
- **Gate_T:** applicable-law check with offence-date semantics and savings rule → `REJECT: TEMPORAL_DRIFT`.
- **Uncertainty:** mutual information `MI > τ_u` → `ABSTAIN`; no forced REJECT.
- Thresholds (`τ_conf`, `τ_u`, `θ`) tuned on dev only.
- Output: `PASS | REJECT(reason) | ABSTAIN`. Report FPR with abstentions counted as accept and as reject.

**Repair module (not "agentic" unless it earns it).** Candidate paragraphs from the same judgment: BM25 + bi-encoder, cross-encoder rerank, re-run Gate_R/Gate_S. Statutory repair returns the corresponding provision and a flagged note; proposition rewriting off by default.

## 6. Phase 4: Experiments 

**Baselines**

- B1: legalcite-support-base (domain-shift probe)
- B2: in-domain fine-tuned cross-encoder
- B3: current frontier LLMs, base prompt
- B4: same, +Gnd. prompt (Verma replication)
- B5: LLM + role-aware prompt / role tags (separates information from architecture)
- B6: retrieval-only top-k paragraph check

**Ablations**

| ID | Variant | Tests |
| --- | --- | --- |
| A0 | Full system | — |
| A1 | Full paragraph into NLI (no role filter) | H2 |
| A2 | Role-filtered input, no hard Gate_R | Input filter vs. rule |
| A3 | Hard Gate_R only, no NLI | Rule alone |
| A4 | No temporal gate | Tier 5 |
| A5 | No abstention | H3 |
| A6 | Oracle roles | H4 |
| A7 | Shuffled roles (control) | Role signal is real |

**Metrics:** recall per tier, FPR, precision, F1, AUROC, risk-coverage/AURC, ECE, abstention rate. Wilson 95% CIs; McNemar on paired items; bootstrap over cases (not items); ≥ 3 seeds for trained components. Repair: Hit@1/3 on any-valid sets; latency and tokens measured against the cited-page baseline for verification and against full-judgment input for repair, including tagger cost.

**Error analysis:** per-role confusion, false rejections of valid citations by role, multi-issue judgments, temporal edge types, annotator-disagreement subset.

## 7. Pre-Submission Cross-Check Checklist

- [ ] No `case_id` overlap across train/dev/test; thresholds touched only dev
- [ ] Tagger-independent benchmark subset reported
- [ ] κ ≥ 0.7 for T3, T4, T5 labels and graph edges
- [ ] "Valid" citation audit completed and disputed items removed
- [ ] Contamination probe reported
- [ ] Every number in the abstract traceable to a table; every "first" claim backed by a dated literature search log (Google Scholar, arXiv, ACL Anthology, SSRN)
- [ ] Verma (2026) numbers reproduced on our prompts before claiming comparisons
- [ ] Limitations stated: Supreme Court only, overruling not covered, not legal advice
- [ ] Licensing and release terms checked for judgment sources and datasets

