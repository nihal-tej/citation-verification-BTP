Before we introduced the three-level approach, RhetoriCite-India was primarily a legal citation-support verification system. It assumed the user already had a legal proposition, a case citation, a pinpoint paragraph, and the offence date.

The objective was to verify whether that specific paragraph actually supported the proposition—not to discover citations from scratch.

## 1. What we were doing originally

The original architecture in your Multi-Agent Architecture & Implementation Guide, Section 1, follows this flow:

1. Input: Proposition `P`, citation `C`, pinpoint paragraph `k`, offence date `t`.
2. Resolver Agent: Resolves the cited case and pinpoint paragraph.
3. Segmenter Agent: Identifies sentence-level rhetorical roles and the claim type.
4. Statute Agent: Checks statutory applicability and changes in legislation.
5. Verifier Agent: Uses NLI, uncertainty estimation, and Gates R/S/T to determine whether the citation supports the proposition.
6. Repair Agent: If verification fails, retrieves alternative paragraphs from the same judgment and re-verifies them.
7. Auditor Agent: Reviews uncertain cases and escalates unresolved cases to a human.

The Orchestrator controls the entire workflow.&#x20;

RhetoriCite-India\_ Multi-Agent Architecture & Implementation Guide.md



## 2. What exactly was the system checking?

Suppose the user provided:

- Proposition: The Court held that X.
- Citation: Case A v. State X.
- Pinpoint: Paragraph 25.
- Offence date: 15 March 2023.

The original system would:

- Resolve Case A and paragraph 25.
- Check whether the paragraph contains the court's own reasoning or merely records a party's argument.
- Determine whether the paragraph supports the proposition.
- Check statutory applicability where relevant.
- Return `PASS`, `REJECT`, or `ABSTAIN`.
- If rejected, attempt to find a better supporting paragraph within Case A.

The central research idea was that a citation can point to the correct case and paragraph yet still fail to support the legal claim because of the rhetorical role of the cited text.&#x20;

RhetoriCite-India v2\_ Revised Implementation Plan.md



## 3. What was outside the original scope?

The original architecture did not explicitly define three user-facing levels.

| Capability                                                             | Original design                                         |
| ---------------------------------------------------------------------- | ------------------------------------------------------- |
| Find citations using only a proposition                                | Not explicitly included                                 |
| Verify whether a specified case supports a proposition                 | Not a separate workflow; the system expected a pinpoint |
| Verify a specific pinpoint paragraph                                   | Yes — the primary task                                  |
| Find a replacement paragraph in the same judgment                      | Yes — the repair mechanism                              |
| Search the entire corpus for alternative cases when verification fails | Not the defined repair behaviour                        |

## 4. The fundamental difference

### Original RhetoriCite-India

Verification-first approach

User supplies a claim + case + pinpoint.

The system checks whether that pinpoint supports the claim and repairs it if necessary.

### Your proposed revised RhetoriCite-India

Discovery + verification approach

The user can start with only a claim, provide a claim and case, or provide a claim, case and pinpoint.

The system discovers citations when necessary and verifies them at the appropriate level.

My interpretation: the three-level approach extends the original project rather than replacing its core research contribution. The role-aware verifier, statutory graph, uncertainty handling, and repair mechanism remain relevant. What changes is the entry point and the scope of retrieval.

The original question was:

> Does this particular pinpoint citation support this legal proposition?

Your revised system asks a broader question:

> Can we find appropriate legal citations for a proposition, verify a selected case, and validate the exact pinpoint paragraph—depending on what the user provides?

That is the key distinction between what we were building originally and what you are proposing now.&#x20;