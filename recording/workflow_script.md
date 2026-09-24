# Screen Recording Outline (English, 5-8 minutes)

The assignment requires an actual screen recording. Use this outline while recording the repository and live workflow; camera and slides are optional.

## Privacy before recording

- The source PDF and generated outputs contain borrower/property/loan details. Do not show or read out unredacted values. Use a masked display copy of `result.json` and redact the relevant source-page areas before showing the conflict.
- Close unrelated apps, private chats, notifications, and account details. Review the exported recording before sharing it.

## 0:00-0:45 - Introduce the task

Show the project folder without opening the source PDF or exposing personal values. Say: "This assignment is about classifying pages in a mortgage package, grouping multi-page documents, extracting three loan-level fields, and reconciling conflicting evidence."

## 0:45-1:30 - Show the inputs and output contract

Open `candidate_classification_labels.txt`, `extraction_fields.json`, and a masked display copy of `result.json`. Point out that all 12 source pages receive a label and extracted fields keep source-page references. Keep borrower, address, and loan-number values masked.

## 1:30-2:30 - Explain the prompts

Show `prompts/page_classification.md`, `prompts/field_extraction.md`, and `AI_WORKFLOW.md`. Explain continuation context, field extraction, the tools and checks used, and why conflicts are retained for review. Do not open hidden Codex instructions or expose account settings.

## 2:30-3:45 - Walk through the implementation

Open `src/loan_pipeline.py`. Show the cue-based classifier, grouping by adjacent labels, printed-page-order handling, evidence scoring by distinct document group, and structural validation before writing JSON.

## 3:45-4:45 - Run the local workflow

Run `python src/loan_pipeline.py`. Show the summary, then use only the masked display copy when showing the JSON; do not leave the raw generated output visible in the recording.

## 4:45-6:00 - Discuss the real conflict

Show only redacted/cropped views of source pages 1 and 2. Explain that they contain two different loan-number observations and that page 2 was checked against the source. Do not read or display either identifier. Show how the output compares distinct document groups, keeps both observations in the conflict record, and requires human review.

## 6:00-7:00 - Show review and limitations

Show the note's internal page order `[7, 8, 10, 9]` and the coordinate-based address fallback. Explain the first-pass false match (`Borrower Did Not Shop For`) and how source review led to a role-aware fix. Mention that scanned-only PDFs need OCR and the confidence scores are not calibrated probabilities.
