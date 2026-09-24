# Screen Recording Outline (English, 5-8 minutes)

The assignment requires an actual screen recording. Use this outline while recording the repository and live workflow; camera and slides are optional.

## Privacy before recording

- The source PDF may contain borrower/property/loan details. The pipeline redacts these values in `result.json` before writing it; confirm the placeholders are visible before recording. Do not show or read out source identifiers. Crop or redact the relevant source-page areas before showing the conflict.
- Close unrelated apps, private chats, notifications, and account details. Review the exported recording before sharing it.

## 0:00-0:45 - Introduce the task

Show the project folder without opening the source PDF or exposing personal values. Say: "This assignment is about classifying pages in a mortgage package, grouping multi-page documents, extracting three loan-level fields, and reconciling conflicting evidence."

## 0:45-1:30 - Show the inputs and output contract

Open `candidate_classification_labels.txt`, `extraction_fields.json`, and `result.json`. Point out that all 12 source pages receive a label, extracted fields keep source-page references, and borrower/property/loan identifiers are replaced by stable placeholders before the file is written.

## 1:30-2:30 - Explain the prompts

Show `prompts/page_classification.md`, `prompts/field_extraction.md`, and `AI_WORKFLOW.md`. Explain continuation context, field extraction, the tools and checks used, and why conflicts are retained for review. Do not open hidden Codex instructions or expose account settings.

## 2:30-3:45 - Walk through the implementation

Open `src/loan_pipeline.py`. Show the cue-based classifier, grouping by adjacent labels, printed-page-order handling, evidence scoring by distinct document group, and structural validation before writing JSON.

## 3:45-4:45 - Run the local workflow

Run `python src/loan_pipeline.py`. Show the summary and the generated JSON. Explain that the pipeline redacts sensitive identifiers before writing the output, while retaining evidence pages and conflict status.

## 4:45-6:00 - Discuss the real conflict

Show only redacted/cropped views of source pages 1 and 2. Explain that they contain two different loan-number observations and that page 2 was checked against the source before redaction. Do not read or display either identifier. Show how the output compares distinct document groups, keeps both placeholder observations in the conflict record, and requires human review. State that redaction protects the submitted artifact but prevents viewers from directly comparing the placeholder values with the source.

## 6:00-7:00 - Show review and limitations

Show the note's internal page order `[7, 8, 10, 9]` and the coordinate-based address fallback. Explain the first-pass false match (`Borrower Did Not Shop For`) and how source review led to a role-aware fix. Mention that scanned-only PDFs need OCR and the confidence scores are not calibrated probabilities.
