# AI Workflow Summary

## Tools / Harnesses Used

- OpenAI Codex Desktop for document analysis, prompt drafting, implementation, and review.
- Python 3.12 with `pdfplumber` for local PDF text and word-coordinate extraction; `pdftoppm` for page-image review; Git for version control.
- No paid LLM API or external data connector was used. No agents were delegated.

## Repository Instructions / Agent Configuration

- `AI_WORKFLOW_TEMPLATE.md` was the supplied workflow template.
- The project uses the provided label and field files plus the two prompt files under `prompts/`.
- No `AGENTS.md`, custom agent command, or repository-specific model configuration was used. The local pipeline does not need an API key.

## How I Used the Agent

- I broke the assignment into page classification, document grouping, field extraction, reconciliation, implementation, and final deliverables.
- I supplied the assignment brief, loan PDF, allowed labels, and extraction schema as context. I kept the work in one agent session and reviewed each output against the source pages.
- I used the agent to draft the rule-based baseline and prompt contracts, then made the extraction rules narrower where the PDF layout produced false matches.

## Verification

- I ran the local pipeline and checked that it emitted 12 labels, five document groups, three requested fields, and valid in-range source pages.
- I compared page labels and extracted values with the page text. I visually checked the first three PDF pages, including the printed loan-number mismatch on page 2, and reviewed word coordinates for the Closing Disclosure's Property cell.
- The JSON output has structural checks for page coverage, allowed labels, group partitioning, requested fields, and evidence-page bounds. No dedicated automated test suite was added.

## One Example Where the Agent Was Wrong or Incomplete

The first extraction pass treated any text after the word "Borrower" as a candidate name. That incorrectly captured headings such as "Borrower Did Not Shop For" and "Closing Date." It also read the spaced house number on page 1 as `4` instead of `[REDACTED_ADDRESS_NUMBER]`. I noticed the false values while comparing the generated JSON with the labeled fields and the page image. I changed the name parser to start from an explicit `Borrower(s) Name` field and only use exact matching occurrences as support. For the address, I normalized spaced digits only when they precede a compass direction and added a coordinate-based fallback for the Closing Disclosure's Property cell. The loan-number discrepancy remains visible and requires human review.
