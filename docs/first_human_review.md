# First condition level human review

## Prepare and inspect

Run `python scripts/prepare_first_review.py` from the project root after ingestion. It creates review sheets and a neutral full-source bundle under `data/processed/reviews/api-open-document-13`, which is already ignored by Git. No source is executed and no support labels are assigned. The condition was proposed by the researcher with assistant support; confirm or correct it before labelling.

First inspect `shared/requirement.json`. For this case the proposed condition is: Calling docx.Document() without arguments returns a Document object. Installation is stated as a precondition, not automatically a separate outcome obligation. Decide how its evidence is established, and document the decision. A pass-only Given does not by itself prove either missing validation or sufficient setup. Static source assessment must not claim successful execution.

Then inspect `shared/sources/` and its collection manifest. Record source evidence for the precondition, action and required outcome. An evidence reference should include path, revision, SHA-256, start and end lines, the relevant text and a short explanation. Shared files may contain unrelated tests; do not attribute an assertion to this condition simply because it occurs in a linked file. A helper contributes only when the relevant call and evidence can be justified.

## Initial labels

Edit your own `review.json`. Use these values consistently:

| Field | Values |
|---|---|
| completeness | sufficient, partial, no_support_found, uncertain |
| evidence_route | direct, indirect, mixed, not_applicable, unknown |
| conflict | present, absent, uncertain |
| annotation status | not_started, in_progress, initial_complete |

Sufficient requires evidence of relevant setup, the action and every stated outcome or constraint. Partial means some aspects are supported but an obligation remains unsupported after eligible-collection review. No-support requires a completed review of the entire defined collection. Unavailable context or incomplete review cannot establish absence and should produce uncertainty where they prevent a decision. Preserve supporting and conflicting evidence separately; both can coexist.

For partial or no_support_found, record all reviewed files, the search method, dependencies and collection_review_complete. Use the same discipline before claiming no conflict in the collection. An unchecked dependency does not automatically invalidate a direct assertion, but explain whether it matters. Do not fabricate a numerical constraint where none is stated.

## Independence and later discussion

Confirm a qualified classmate is available. Send the reviewer only the shared requirement and source bundle, this guide and the blank reviewer sheet, after checking redistribution notices. Do not send your completed sheet, assistant conclusions or generated packet warnings. Store their returned initial sheet separately and unchanged. The current researcher has already seen assistant interpretation and framework output; set the relevant exposure fields to true and explain this. Never describe this exercise as fully blinded.

Each person independently confirms the condition, inspects source evidence, chooses labels and writes a rationale. If the reviewer proposes a different condition, record it and resolve segmentation before scoring label agreement. Preserve the original review; do not silently overwrite it. Mark initial_complete only after your actual assessment. Calculate pilot agreement before discussing labels, once the planned pilot is available. One case cannot establish stable agreement, method accuracy or thesis results.

Do not place a guessed final answer in either review sheet. The next research task is identifying and documenting additional development-pilot cases with varied behaviours and helper involvement, without selecting them by favourable framework predictions. Any previously inspected pilot identities must first be recovered or their replacement documented.
