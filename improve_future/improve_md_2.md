Yes, I think this is the right development strategy for RhetoriCite-India. We should first implement the original architecture, establish that citation verification works reliably, and then extend it into the three-level system.

This avoids building citation discovery, case-level verification, and pinpoint verification all at once.

## Phase 1 — Build the original RhetoriCite-India

Initial implementation

Input: Proposition + Citation + Pinpoint paragraph + Offence date

Implement the existing architecture in this order:

1. Resolver: Resolve the cited judgment and pinpoint paragraph.
2. Segmenter: Identify rhetorical roles and classify the proposition.
3. Statute Agent: Extract statutory references and check temporal applicability.
4. Verifier: Implement NLI, Gates R/S/T, and uncertainty handling.
5. Repair Agent: Retrieve alternative paragraphs from the same judgment and re-verify them.
6. Auditor: Review abstentions and escalate unresolved cases.
7. Orchestrator: Connect the components using the existing state machine.

Phase 1 goal: Given an existing pinpoint citation, reliably determine whether it supports the proposition and suggest a better pinpoint when possible.

This follows the implementation guide's build order, which recommends developing the individual components before adding repair and audit functionality.&#x20;

RhetoriCite-India\_ Multi-Agent Architecture & Implementation Guide.md



## Phase 2 — Extend to three levels

Once Phase 1 works, we extend the same system rather than rewrite it.

## 1

Citation discovery

Input: Proposition only

Add corpus-wide retrieval to find relevant cases and paragraphs, then verify the candidates.

## 2

Case-level verification

Input: Proposition + Citation

Add a workflow that searches within the specified judgment, determines whether it supports the proposition, and identifies suitable paragraphs.

## 3

Pinpoint verification

Input: Proposition + Citation + Pinpoint

Reuse the original Phase 1 workflow to verify the exact paragraph and repair the pinpoint if necessary.

## Phase 3 — Integrate the workflows

The Orchestrator will identify the user's input and route it to the appropriate workflow.

| Available input                   | Workflow                |
| --------------------------------- | ----------------------- |
| Proposition only                  | Full-corpus discovery   |
| Proposition + citation            | Case-level verification |
| Proposition + citation + pinpoint | Pinpoint verification   |

All three workflows reuse the same core verification components.

## One important implementation decision

Build Phase 1 so it can be reused in Phase 2 without major changes.

In particular:

- Keep the Verifier independent of how candidate paragraphs were retrieved.
- Let the Resolver accept either a specified citation or a candidate retrieved by the discovery workflow.
- Make the Repair Agent's search scope configurable: same judgment initially, full corpus only when implementing discovery.
- Keep the Orchestrator responsible for routing, not for performing legal reasoning itself.

This will reduce unnecessary restructuring later.

My recommendation: First validate the original system on the pinpoint-verification task. Once its retrieval, role classification, verification, and evaluation are working, add the two broader entry points. That gives us a measurable baseline before expanding the scope of the research.