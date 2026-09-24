# Mortgage Document Understanding

**AREAL.AI NLP / LLM Internship Assignment**  
Design, implementation, and results

## Executive summary

The assignment asks for page classification, document grouping, three loan-level fields, conflict reconciliation, and a working implementation. The 12-page PDF contains five document groups. A local pipeline produces the results and flags the conflicting loan number for human review.

The design uses a hybrid approach: deterministic text and layout rules make the provided example reproducible; the full LLM prompts are maintained in `prompts/page_classification.md` and `prompts/field_extraction.md` for an API-backed extension. The output preserves evidence pages, printed pagination, competing observations, and review flags.

JSON was selected because it keeps page labels, document groups, extracted fields, evidence, conflicts, and review flags in one machine-readable structure that is easy to validate and reuse.

## Page classification and document grouping

| PDF pages | Allowed label | Evidence and handling |
|---|---|---|
| 1-2 | `Property - Tax Record Information Sheet` | Page 1 has the form title; page 2 is the marked continuation. Page 2 contains a conflicting loan number. |
| 3 | `Title - Signature / Name Affidavit (Ack)` | Explicit affidavit title; alternate name forms are kept as a review note. |
| 4-6 | `Title - Rider` | Condominium Rider and form identifier `F3140`; printed pages 1-3. |
| 7-10 | `Lender - Rate Note` | Fixed-rate Note and form identifier `F3200`. PDF pages 7, 8, 10, 9 are the printed sequence 1, 2, 3, 4. |
| 11-12 | `Mortgage - Closing Disclosure - Seller` | Seller Closing Disclosure; page 12 is marked 2a of 2. |

The system keeps 1-based PDF page numbers as source references. It stores printed page markers separately and derives `document_page_order` from those markers when all pages in a group have them. This prevents the note's out-of-order pages from being silently rearranged or misreported.

## Extraction results

| Field | Selected value | Source pages |
|---|---|---|
| `borrower_name` | [REDACTED_BORROWER] | 1, 3, 6, 10, 11 |
| `property_address` | [REDACTED_PROPERTY_ADDRESS] | 1, 3, 4, 7, 11 |
| `loan_number` | [REDACTED_LOAN_ID_1] | 1, 3-10 |

The address is normalized for whitespace and line breaks while preserving the street, unit, city, state, and ZIP code. The affidavit contains alternate name forms; the repeated borrower name in explicit borrower/signature contexts remains canonical.

## Loan-level reconciliation

The tax-record sheet contains conflicting loan numbers: `[REDACTED_LOAN_ID_1]` on PDF page 1 and `[REDACTED_LOAN_ID_2]` on page 2. I checked page 2 against the rendered source; the differing digits are present in the document, so I did not silently correct them. The extractor removes only spaces and hyphens from an explicitly labeled eight-digit loan-number candidate; it preserves digit order and does not guess replacement digits.

The first candidate is supported by PDF pages 1, 3-10 across four distinct groups: DOC-01 Tax Record (weight 2), DOC-02 Affidavit (2), DOC-03 Rider (3), and DOC-04 Rate Note (4), for a summed reliability score of 11. The second candidate appears on page 2 in DOC-01 only (one group, weight 2). The ranking compares distinct-group count first, then the configured document-type weight; repeated pages within a group count once. This makes `[REDACTED_LOAN_ID_1]` the better-supported value, not a verified truth. The pipeline preserves both observations, selects the first provisionally, sets `review_required`, and raises a high-severity human-review flag.

The reported confidence is `0.88`. It is a heuristic evidence-strength score capped because a conflict exists; it is not a model probability and is not used to choose between values. There is no live LLM in this baseline, so no model-generated confidence signal is available. Selection instead rests on the visible source-page evidence and agreement across distinct documents. An authoritative loan system or source file must resolve the discrepancy.

The extraction prompt defines `property_address` as the mortgaged property rather than a mailing address, and `loan_number` as an identifier rather than a MIN, file number, or amount. The local loan-number parser enforces an explicit loan-number label. Address extraction currently scans page text for address patterns and adds a coordinate-based fallback for the Closing Disclosure's `Property` cell; it does not yet classify the semantic role of every address occurrence across arbitrary documents. Broader deployment would require role-aware address filtering and validation against more document layouts.

## Field extraction design and trade-offs

`extraction_fields.json` lists `borrower_name`, `property_address`, and `loan_number`. Extraction starts after every page is classified and adjacent pages are grouped. The baseline reads each page for field evidence, then reconciles values at loan level. This keeps page citations precise while groups provide context and count as one source. The LLM prompt follows the same sequence, with candidate pages grouped by `document_id`.

The prompt returns each value with source pages, supporting documents, confidence, review flag, and notes; a `conflicts` list preserves alternatives. This is auditable and easy to validate, though more verbose than flat values.

For a future LLM call, grouped candidate pages preserve context and can reduce token use. The current baseline scans all page text locally, makes no API calls, and runs the same rules reproducibly. Explicit patterns and the layout fallback help on this package but may miss unfamiliar formats. Validation checks page coverage, labels, field keys, and evidence-page ranges.

No extractable text stops the run with an OCR instruction. Missing fields return `null` and require review; conflicts are preserved and ties remain unresolved rather than guessed.

## Prompt design

The classification prompt requires one allowed label per input page, uses adjacent pages only as context, preserves PDF page references, and makes weak evidence visible with a lower confidence score and a concise note. The extraction prompt defines the roles of borrower name, property address, and loan number; requires page references; and preserves all competing observations rather than silently resolving them.

Both prompts treat document text as untrusted evidence rather than instructions. Their complete system and user wording and JSON contracts are included in the two files under `prompts/`. Confidence is explicitly described as a heuristic evidence-strength score, not a calibrated probability.

## Implementation and additional ideas

Run the local pipeline with `python src/loan_pipeline.py`. It reads the provided PDF, label list, and field schema, then writes `result.json`.

- **Distinct-document evidence:** reconciliation groups repeated values by document before scoring them, avoiding false confidence from duplicated page headers.
- **Layout-aware fallback:** the Closing Disclosure's text extractor interleaves neighboring columns. The address extractor uses word coordinates to read only the Property cell when ordinary text order is unreliable.
- **Structural validation:** before writing output, the pipeline checks that every PDF page has one allowed label, document groups partition the pages, fields match the requested schema, and evidence page references are in range.
- **Review queue:** conflicts and layout/order issues become machine-readable `quality_flags`, so downstream workflow can route only questionable records to a person.
- **Separate source and document order:** page evidence retains original PDF locations while internal printed order is captured independently.

The local implementation is a deterministic baseline, not a live LLM call. This keeps the example reproducible without credentials and creates a reference against which later model output can be compared. The supplied PDF has selectable text; the pipeline stops on a page without extractable text and requires an OCR stage for scanned-only input. Confidence weights and address patterns are assignment-specific and need calibration and broader document coverage before production use.

## Verification

The pipeline was run against the supplied PDF. The generated output contains 12 page labels, five document groups, and all three requested fields. The output structure and source-page references were checked; pages 1-3 were visually reviewed, including the loan-number mismatch on page 2. The note's printed page sequence and the Closing Disclosure's Property cell were also checked against their page text/layout. No dedicated automated test suite is included in this small assignment implementation.

## First-pass errors I found and corrected

When reviewing the first output against the source PDF, I found two errors: headings were captured as borrower names, and the house number text was misread. I narrowed name extraction to the explicit `Borrower(s) Name` field and corrected address handling with contextual digit normalization and a coordinate-based fallback for the Closing Disclosure's Property cell. After rerunning and checking the values, I kept the different loan number on page 2 visible as a conflict requiring human review.
