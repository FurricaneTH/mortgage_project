# AI Workflow Summary

## Tools / Harnesses Used

- OpenAI Codex Desktop (GPT-5-based). The exact model ID and reasoning setting were not exposed in the task record, so I have not guessed them.
- Python 3.12.14 with `pdfplumber` for PDF text/word coordinates and ReportLab for the report; Poppler `pdftoppm` for visual PDF review; Git for version control.
- Codex's built-in PDF skill guided report generation and visual review. No paid LLM API, API key, external data connector, or project-configured MCP server was used.

## Repository Instructions / Agent Configuration

- `AI_WORKFLOW_TEMPLATE.md` was the supplied template. `prompts/page_classification.md` and `prompts/field_extraction.md` are project prompt contracts, not runtime agent configuration.
- No `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, repository skill, custom agent command, or model configuration was present. `.vscode/extensions.json` only recommends an editor extension; it does not add project instructions.
- The pipeline is a local deterministic baseline and does not call an LLM.

## How I Used the Agent

- I supplied the assignment brief, loan PDF, allowed labels, and field schema. I worked through classification, grouping, extraction, reconciliation, implementation, and deliverables in that order because later decisions depended on earlier page evidence.
- Codex handled source inspection, prompt/code/report edits, and local runs. I set the requirements, reviewed the resulting decisions and explanations, and steered corrections. No sub-agents were delegated: the tasks shared one source package and required a continuous evidence trail, so separate agent roles would have added handoff overhead without independent work.

## Verification

- I ran `python src/loan_pipeline.py` with the supplied PDF. The run produced 12 page labels, five document groups, three loan fields, and a high-severity review flag for the loan-number conflict.
- The pipeline validates full page coverage, allowed labels, non-overlapping document groups, requested field keys, and in-range evidence pages before writing JSON. I compared the generated output with the source pages, including the page 2 number conflict, printed page order, and the Closing Disclosure Property cell.
- The pipeline now replaces borrower, property, and loan identifiers with stable placeholders before writing JSON. Page evidence, agreement counts, conflict status, and review flags remain visible; exact identifier comparison is limited to the authorized local source review. The report and recording use the same privacy policy.
- I rendered and visually reviewed the report PDF after edits. No separate automated unit-test suite was added; verification used the executable pipeline, built-in structural checks, source-page review, and PDF rendering.

## One Example Where the Agent Was Wrong or Incomplete

The first extraction pass treated any text after “Borrower” as a possible borrower name, which captured headings such as “Borrower Did Not Shop For” and “Closing Date.” It also read the spaced house number `[REDACTED_ADDRESS_NUMBER]` on page 1 as `4`. I found these mismatches while comparing the output with the labeled fields and source page. I narrowed name extraction to the explicit `Borrower(s) Name` field, made spaced-digit normalization conditional on a following compass direction, and added a coordinate-based fallback for the Closing Disclosure Property cell. I reran the pipeline and kept the separate loan-number discrepancy visible for human review.
