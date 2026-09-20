# Mortgage Document Understanding

**AREAL.AI NLP / LLM Internship Assignment**  
Design, implementation, and results

## Executive summary

The assignment asks for page-level classification, logical document grouping, extraction of three loan-level fields, conflict reconciliation, and a small working implementation. The supplied PDF contains 12 pages from five document groups. The implementation produces structured JSON locally, without a paid model API, and sends the conflicting loan number to human review.

The design uses a hybrid approach: deterministic text and layout rules make the provided example reproducible; the full LLM prompts are maintained in `prompts/page_classification.md` and `prompts/field_extraction.md` for an API-backed extension. The output preserves evidence pages, printed pagination, competing observations, and review flags.

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

The tax-record sheet prints `[REDACTED_LOAN_ID_1]` on page 1 and `[REDACTED_LOAN_ID_2]` on its continuation page 2. Page 2 was visually checked; the differing digits are printed in the PDF. The value `[REDACTED_LOAN_ID_1]` also appears in the affidavit, rider, and rate note. The pipeline therefore selects `[REDACTED_LOAN_ID_1]`, but sets `review_required` and emits a high-severity quality flag.

Reconciliation uses distinct document groups and simple document-type reliability weights. Repeated occurrences on pages of one document do not count as separate confirmations. If the top observations tie, the code leaves the value unresolved. The selected value is a best-supported result, not a claim that the source discrepancy is harmless.

The Closing Disclosure's sale-price field and the Note's principal field describe different concepts and should not be treated as duplicate observations. Field-role checks also prevent a seller's mailing address or the document's MIN/file number from replacing the requested borrower, property, or loan-number fields.

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

## AI workflow

The tools, review process, and one concrete first-pass extraction error are documented in `AI_WORKFLOW.md`. The required five-to-eight-minute English screen recording should show the actual repository, prompts, local run, output, and manual review.
