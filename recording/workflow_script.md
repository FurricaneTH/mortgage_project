# Screen Recording Outline (English, 5-8 minutes)

The assignment requires an actual screen recording. Use this outline while recording the repository and live workflow; camera and slides are optional.

## 0:00-0:45 - Introduce the task

Show the project folder and say: "This assignment is about classifying pages in a mortgage package, grouping multi-page documents, extracting three loan-level fields, and reconciling conflicting evidence."

## 0:45-1:30 - Show the inputs and output contract

Open `candidate_classification_labels.txt`, `extraction_fields.json`, and `result.json`. Point out that all 12 source pages receive a label and the extracted values include source page references.

## 1:30-2:30 - Explain the prompts

Show `prompts/page_classification.md` and `prompts/field_extraction.md`. Explain continuation context, allowed labels, source-page references, role-aware field extraction, and why conflicts are retained for review.

## 2:30-3:45 - Walk through the implementation

Open `src/loan_pipeline.py`. Show the cue-based classifier, grouping by adjacent labels, printed-page-order handling, evidence scoring by distinct document group, and structural validation before writing JSON.

## 3:45-4:45 - Run the local workflow

Run `python src/loan_pipeline.py`. Show the summary and open the regenerated `result.json`.

## 4:45-6:00 - Discuss the real conflict

Show source PDF pages 1 and 2. Explain that page 1 prints `[REDACTED_LOAN_ID_1]`, page 2 prints `[REDACTED_LOAN_ID_2]`, and the latter was visually checked. Show how the output selects the value supported across distinct document groups while keeping a human-review flag.

## 6:00-7:00 - Show review and limitations

Show the note's internal page order `[7, 8, 10, 9]` and the coordinate-based address fallback. Explain the first-pass false match (`Borrower Did Not Shop For`) and how source review led to a role-aware fix. Mention that scanned-only PDFs need OCR and the confidence scores are not calibrated probabilities.
