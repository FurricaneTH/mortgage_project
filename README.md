# AREAL Mortgage Document Understanding

This project classifies the pages in `AREAL_LOAN.pdf`, groups adjacent pages into logical documents, extracts the three requested loan-level fields, and records conflicting evidence for review.

## Run locally

Use Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/loan_pipeline.py
python report/build_report.py
```

The default command reads `AREAL_LOAN.pdf`, `candidate_classification_labels.txt`, and `extraction_fields.json` from the project directory and writes `result.json` there. Paths can be overridden:

```bash
python src/loan_pipeline.py --input path/to/package.pdf --labels path/to/labels.txt --fields path/to/fields.json --output path/to/result.json
```

`AREAL_LOAN.pdf` is intentionally excluded from version control because it contains loan and borrower details. On a fresh checkout, place the authorized assignment-provided PDF in the project root before running the default command.

## Design

- The local baseline uses weighted title, form-code, and content cues. It reads the allowed labels from the supplied label file and fails if the classifier rules drift from that list.
- Adjacent pages with the same label are grouped. Printed page markers are kept separately from 1-based PDF page references, so the Fixed-rate Note's internal order anomaly remains visible.
- Field extraction uses labeled borrower and loan-number patterns, address normalization, and a coordinate-based fallback for the Closing Disclosure's multi-column property cell.
- Reconciliation counts distinct document groups and applies simple document-type weights. Repeated mentions inside one document do not count as independent confirmation. Ties remain unresolved, and material conflicts create a review flag.
- The confidence values are heuristic evidence-strength scores, not calibrated probabilities.
- `prompts/` contains the proposed LLM prompts. The Python baseline runs without a model API or API key, making it possible to inspect and reproduce the provided example locally.

## Files

- `src/loan_pipeline.py`: PDF reading, classification, grouping, extraction, and reconciliation.
- `prompts/page_classification.md`: page-classification prompt and output contract.
- `prompts/field_extraction.md`: extraction prompt and conflict-handling contract.
- `result.json`: generated structured output with evidence page references and review flags.
- `AI_WORKFLOW.md`: tools used and the human review workflow.
- `report/report.pdf`: design report.
- `report/build_report.py`: rebuild the PDF from `report/report.md`.
- `recording/workflow_script.md`: timed outline for the required English screen recording.

## Known limits

This is a small, assignment-specific baseline, not a production mortgage-processing system. It expects selectable text in the PDF; pages without extractable text stop with an actionable error and need OCR before classification. The address patterns cover common U.S. formats and should be expanded before use on a broader corpus. Any loan-number conflict is routed for human review.

The supplied loan package contains personal and financial details. Keep `AREAL_LOAN.pdf` local and do not publish it.
