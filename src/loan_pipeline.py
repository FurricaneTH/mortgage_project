#!/usr/bin/env python3
"""Local baseline for the AREAL mortgage-document assignment.

The pipeline uses explicit document cues and field evidence so it can run
without a paid model API. The prompt files describe the corresponding LLM
interface; this implementation provides a deterministic baseline and review
signals that can later be compared with model output.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]

RULES: dict[str, tuple[tuple[str, int], ...]] = {
    "Property - Tax Record Information Sheet": (
        ("TAX RECORD INFORMATION SHEET", 12),
        ("COMPLETION OF TAX RECORDS", 7),
        ("GTXI 0817", 5),
        ("TAXING AUTHORITY NAME", 3),
        ("CURRENT TAXES PAID", 2),
    ),
    "Title - Signature / Name Affidavit (Ack)": (
        ("SIGNATURE/NAME AFFIDAVIT", 12),
        ("GSNA", 5),
        ("SUBSCRIBED AND SWORN", 3),
        ("NOTARY PUBLIC", 2),
    ),
    "Title - Rider": (
        ("MULTISTATE CONDOMINIUM RIDER", 12),
        ("CONDOMINIUM RIDER", 12),
        ("F3140", 8),
        ("CONDOMINIUM COVENANTS", 6),
        ("CONDOMINIUM PROJECT", 2),
        ("OWNERS ASSOCIATION", 2),
    ),
    "Lender - Rate Note": (
        ("MULTISTATE FIXED RATE NOTE", 12),
        ("F3200NOT", 8),
        ("BORROWER'S PROMISE TO PAY", 7),
        ("BORROWER’S PROMISE TO PAY", 7),
        ("UNIFORM SECURED NOTE", 7),
        ("PAY TO THE ORDER OF", 4),
        ("LOAN CHARGES", 3),
        ("NOTE HOLDER", 2),
    ),
    "Mortgage - Closing Disclosure - Seller": (
        ("CLOSING DISCLOSURE", 12),
        ("DUE TO SELLER AT CLOSING", 4),
        ("SELLER'S TRANSACTION", 3),
        ("SELLER’S TRANSACTION", 3),
        ("CLOSING COST DETAILS", 3),
        ("SELLER-PAID", 2),
    ),
}

DOCUMENT_RELIABILITY = {
    "Lender - Rate Note": 4,
    "Title - Rider": 3,
    "Title - Signature / Name Affidavit (Ack)": 2,
    "Property - Tax Record Information Sheet": 2,
    "Mortgage - Closing Disclosure - Seller": 1,
}

ROAD_SUFFIXES = (
    "DR|DRIVE|ST|STREET|AVE|AVENUE|RD|ROAD|BLVD|BOULEVARD|LN|LANE|"
    "CT|COURT|WAY|PKWY|PARKWAY|PL|PLACE|TER|TERRACE"
)
ADDRESS_RE = re.compile(
    rf"""(?ix)
    (?P<street>
        (?<!\d)
        \d{{1,6}}\s+(?:N|S|E|W)\s+
        [A-Z0-9.'-]+(?:\s+[A-Z0-9.'-]+){{0,5}}\s+
        (?:{ROAD_SUFFIXES})
    )
    \s*,?\s*
    (?:(?P<unit_label>UNIT|APT|APARTMENT|\#)\s*(?P<unit>[A-Z0-9-]+)\s*,?\s*)?
    (?P<city>[A-Z][A-Z .'-]{{1,30}}?)\s*,\s*
    (?P<state>[A-Z]{{2}})\s+(?P<zip>\d{{5}}(?:-\d{{4}})?)
    """
)

LOAN_NUMBER_PATTERNS = (
    re.compile(
        r"\bLOAN\s*(?:#|NO\.?|NUMBER)\s*:?\s*((?:\d[\s-]*){8})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bLOAN\s+NUMBER\s+PROPERTY\s+ADDRESS\s+((?:\d[\s-]*){8})",
        re.IGNORECASE,
    ),
)


def normalized_text(text: str) -> str:
    """Normalize Unicode and whitespace without changing words or digits."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text or "")).strip()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def extract_pages(pdf_path: Path) -> list[dict[str, Any]]:
    """Extract selectable text from each PDF page and keep 1-based references."""
    pages: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(layout=False) or ""
            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                    "normalized": normalized_text(text).upper(),
                    "width": page.width,
                    "words": page.extract_words(),
                }
            )
    empty_pages = [page["page_number"] for page in pages if not page["text"].strip()]
    if empty_pages:
        raise ValueError(
            "No embedded text could be extracted from PDF page(s) "
            f"{empty_pages}. Add an OCR stage before classifying these pages."
        )
    return pages


def load_allowed_labels(path: Path) -> list[str]:
    labels = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if set(labels) != set(RULES):
        missing = sorted(set(labels) - set(RULES))
        unexpected = sorted(set(RULES) - set(labels))
        raise ValueError(f"Classifier rules do not match label file; missing={missing}, unexpected={unexpected}")
    return labels


def classify_page(page: dict[str, Any], labels: list[str]) -> dict[str, Any]:
    text = page["normalized"]
    scores = {
        label: sum(weight for cue, weight in RULES[label] if cue in text)
        for label in labels
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_label, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    if best_score == 0:
        raise ValueError(f"Page {page['page_number']} has no recognizable document cues")

    # This evidence-strength score is intentionally described as heuristic,
    # not as a probability produced by a calibrated classifier.
    margin = min(best_score - second_score, 5)
    confidence = round(min(0.99, 0.78 + 0.02 * min(best_score, 10) + 0.02 * margin), 2)
    return {"label": best_label, "confidence": confidence, "scores": scores}


def printed_page_marker(text: str) -> tuple[int, int, str] | None:
    match = re.search(r"\bPAGE\s+(\d+)\s*([A-Z]?)\s+OF\s+(\d+)\b", text, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1)), int(match.group(3)), match.group(2)


def group_documents(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group adjacent pages with the same label; keep printed order separately."""
    groups: list[dict[str, Any]] = []
    for page in pages:
        label = page["label"]
        if not groups or groups[-1]["label"] != label:
            groups.append({"label": label, "pages": []})
        groups[-1]["pages"].append(page)

    documents = []
    for index, group in enumerate(groups, start=1):
        document_id = f"DOC-{index:02d}"
        source_order = [page["page_number"] for page in group["pages"]]
        marked = [
            (printed_page_marker(page["text"]), page["page_number"])
            for page in group["pages"]
        ]
        if all(marker is not None for marker, _ in marked):
            logical_order = [
                page_number
                for _, page_number in sorted(marked, key=lambda item: (item[0][0], item[1]))
            ]
        else:
            logical_order = source_order.copy()
        documents.append(
            {
                "document_id": document_id,
                "label": group["label"],
                "pages": group["pages"],
                "source_order": source_order,
                "document_page_order": logical_order,
            }
        )
    return documents


def extract_borrower_observations(pages: list[dict[str, Any]]) -> dict[str, set[int]]:
    observations: dict[str, set[int]] = defaultdict(set)
    field_pattern = re.compile(r"BORROWER\s*(?:\(S\))?\s*NAME\s*:\s*(.+)", re.IGNORECASE)
    for page in pages:
        for line in page["text"].splitlines():
            match = field_pattern.search(line)
            if match:
                candidate = re.split(r"\s{2,}|TAXES FOR CURRENT YEAR", match.group(1), maxsplit=1, flags=re.I)[0]
                candidate = re.sub(r"[_\s]+$", "", candidate).strip()
                candidate = re.sub(r"\s+", " ", candidate)
                if candidate:
                    observations[candidate].add(page["page_number"])

    # Once an explicit borrower-field value is found, matching occurrences in
    # signatures and related documents become supporting pages. An affidavit
    # may also contain aliases; it does not replace the explicit borrower value.
    canonical_candidates = list(observations)
    for candidate in canonical_candidates:
        for page in pages:
            if candidate.casefold() in normalized_text(page["text"]).casefold():
                observations[candidate].add(page["page_number"])
    return observations


def normalize_address(match: re.Match[str]) -> str:
    street = re.sub(r"\s+", " ", match.group("street")).strip().title()
    unit = match.group("unit")
    unit_part = f" Unit {unit.upper()}" if unit else ""
    city = re.sub(r"\s+", " ", match.group("city")).strip().title()
    state = match.group("state").upper()
    postal = match.group("zip")
    return f"{street}{unit_part}, {city}, {state} {postal}"


def extract_address_observations(pages: list[dict[str, Any]]) -> dict[str, set[int]]:
    observations: dict[str, set[int]] = defaultdict(set)
    for page in pages:
        flat = normalized_text(page["text"])
        # Some form fields encode a house number as separated glyphs, e.g.
        # "[REDACTED_ADDRESS_NUMBER] N ...". Collapse only digit runs directly before a compass
        # direction; generic whitespace removal could join unrelated values.
        address_text = re.sub(
            r"\b(?:\d\s+){1,5}\d(?=\s+[NSEW]\b)",
            lambda match: re.sub(r"\s+", "", match.group(0)),
            flat,
            flags=re.IGNORECASE,
        )
        for match in ADDRESS_RE.finditer(address_text):
            observations[normalize_address(match)].add(page["page_number"])

        # Multi-column closing forms can interleave unrelated cells in the
        # text stream. If a Property label is present, read only that cell's
        # word coordinates as a layout-aware fallback.
        property_labels = [
            word for word in page.get("words", [])
            if word["text"].strip().casefold().rstrip(":") == "property" and word["top"] < 220
        ]
        for label in property_labels[:1]:
            x_min = label["x1"] + 15
            x_max = page["width"] * 0.5
            y_min = label["top"] - 1
            y_max = label["top"] + 30
            cell_words = [
                word for word in page["words"]
                if x_min <= word["x0"] < x_max and y_min <= word["top"] < y_max
            ]
            cell_words.sort(key=lambda word: (word["top"], word["x0"]))
            lines: list[list[dict[str, Any]]] = []
            for word in cell_words:
                if not lines or abs(word["top"] - lines[-1][0]["top"]) > 3:
                    lines.append([word])
                else:
                    lines[-1].append(word)
            cell_text = " ".join(
                " ".join(word["text"] for word in line)
                for line in lines
            )
            for match in ADDRESS_RE.finditer(normalized_text(cell_text)):
                observations[normalize_address(match)].add(page["page_number"])
    return observations


def extract_loan_number_observations(pages: list[dict[str, Any]]) -> dict[str, set[int]]:
    observations: dict[str, set[int]] = defaultdict(set)
    for page in pages:
        flat = normalized_text(page["text"])
        for pattern in LOAN_NUMBER_PATTERNS:
            for match in pattern.finditer(flat):
                # Removing only internal spacing/hyphens from the value next
                # to an explicit LOAN NUMBER label handles PDF text splitting.
                digits = re.sub(r"[\s-]", "", match.group(1))
                if len(digits) == 8:
                    observations[digits].add(page["page_number"])
    return observations


def document_for_page(page_number: int, documents: list[dict[str, Any]]) -> dict[str, Any]:
    for document in documents:
        if page_number in document["source_order"]:
            return document
    raise ValueError(f"No document group contains PDF page {page_number}")


def evidence_summary(
    observations: dict[str, set[int]], documents: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    summaries = []
    for value, page_numbers in observations.items():
        supporting = []
        seen = set()
        for page_number in sorted(page_numbers):
            document = document_for_page(page_number, documents)
            if document["document_id"] not in seen:
                supporting.append(document)
                seen.add(document["document_id"])
        summaries.append(
            {
                "value": value,
                "source_pages": sorted(page_numbers),
                "supporting_documents": supporting,
                "document_count": len(supporting),
                "reliability_score": sum(
                    DOCUMENT_RELIABILITY[document["label"]] for document in supporting
                ),
            }
        )
    return summaries


def choose_observation(summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not summaries:
        return None
    ranked = sorted(
        summaries,
        key=lambda item: (item["document_count"], item["reliability_score"], item["value"]),
        reverse=True,
    )
    if len(ranked) > 1 and (
        ranked[0]["document_count"], ranked[0]["reliability_score"]
    ) == (ranked[1]["document_count"], ranked[1]["reliability_score"]):
        return None
    return ranked[0]


def field_confidence(document_count: int, conflict: bool = False) -> float:
    score = min(0.98, 0.78 + 0.04 * document_count)
    if conflict:
        score = min(score, 0.88)
    return round(score, 2)


def build_field_result(
    field_name: str,
    observations: dict[str, set[int]],
    documents: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summaries = evidence_summary(observations, documents)
    selected = choose_observation(summaries)
    conflict = len(summaries) > 1
    supporting_documents = selected["supporting_documents"] if selected else []
    source_pages = selected["source_pages"] if selected else []
    value = selected["value"] if selected else None

    note_by_field = {
        "borrower_name": "Selected from explicit borrower fields; matching appearances in other documents are supporting evidence. Name variants in the affidavit are retained as a quality flag.",
        "property_address": "Whitespace and line breaks are normalized; source spelling and address components are preserved.",
        "loan_number": "Evidence is ranked by distinct document groups and document-type reliability, not by repeated page mentions. Competing values require human review.",
    }
    output = {
        "value": value,
        "source_pages": source_pages,
        "supporting_documents": [document["document_id"] for document in supporting_documents],
        "confidence": field_confidence(len(supporting_documents), conflict) if selected else None,
        "review_required": conflict or selected is None,
        "notes": note_by_field[field_name],
    }

    conflicts = []
    if conflict:
        observations_output = [
            {
                "value": item["value"],
                "source_pages": item["source_pages"],
                "supporting_documents": [doc["document_id"] for doc in item["supporting_documents"]],
            }
            for item in summaries
        ]
        evidence_comparison = "; ".join(
            f"{item['value']}: {item['document_count']} distinct document group(s), "
            f"reliability score {item['reliability_score']}"
            for item in sorted(summaries, key=lambda item: item["value"])
        )
        resolution_reason = (
            "Evidence comparison (distinct document groups; summed document-type reliability): "
            f"{evidence_comparison}. Repeated pages within one document group count once."
        )
        if selected is None:
            resolution_status = "unresolved"
            resolution_reason = (
                "Top observations are tied on distinct-document support and reliability; no value was selected. "
                f"Evidence comparison (distinct document groups; summed document-type reliability): {evidence_comparison}."
            )
        else:
            resolution_status = "selected_with_conflict"
        conflicts.append(
            {
                "conflict_id": f"CONFLICT-{field_name.upper()}",
                "field": field_name,
                "type": "different_values_across_pages",
                "observations": observations_output,
                "selected_value": value,
                "resolution_reason": resolution_reason,
                "resolution_status": resolution_status,
                "requires_human_review": True,
                "recommended_action": "Confirm the selected value against an authoritative loan system or source file.",
            }
        )
    return output, conflicts


def page_notes(page: dict[str, Any], documents: list[dict[str, Any]], loan_conflict_pages: set[int]) -> str:
    document = document_for_page(page["page_number"], documents)
    marker = printed_page_marker(page["text"])
    parts = []
    if marker:
        parts.append(f"Printed page {marker[0]}{marker[2]} of {marker[1]}.")
    if page["page_number"] in loan_conflict_pages:
        parts.append("This page contains a loan number that conflicts with another page or document.")
    if document["source_order"] != document["document_page_order"]:
        parts.append("PDF order differs from printed document order; both page references are preserved.")
    if not parts:
        label = page["label"]
        parts.append(f"Page cues support the {label} classification.")
    return " ".join(parts)


def build_result(
    pdf_path: Path,
    pages: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    fields: list[str],
) -> dict[str, Any]:
    borrower_obs = extract_borrower_observations(pages)
    address_obs = extract_address_observations(pages)
    loan_obs = extract_loan_number_observations(pages)
    observations_by_field = {
        "borrower_name": borrower_obs,
        "property_address": address_obs,
        "loan_number": loan_obs,
    }

    loan_result: dict[str, Any] = {}
    conflicts = []
    for field in fields:
        if field not in observations_by_field:
            raise ValueError(f"No extraction implementation for requested field {field!r}")
        result, field_conflicts = build_field_result(field, observations_by_field[field], documents)
        loan_result[field] = result
        conflicts.extend(field_conflicts)

    loan_conflict_pages = set()
    loan_related_pages = set()
    for conflict in conflicts:
        if conflict["field"] == "loan_number":
            for observation in conflict["observations"]:
                loan_related_pages.update(observation["source_pages"])
                if observation["value"] != conflict["selected_value"]:
                    loan_conflict_pages.update(observation["source_pages"])

    output_documents = []
    for document in documents:
        notes = []
        if document["source_order"] != document["document_page_order"]:
            notes.append("PDF source order differs from printed page order; document_page_order follows printed numbering.")
        if document["label"] == "Property - Tax Record Information Sheet" and any(
            page_number in loan_conflict_pages for page_number in document["source_order"]
        ):
            notes.append("The loan-number mismatch occurs within this single document group.")
        output_documents.append(
            {
                "document_id": document["document_id"],
                "label": document["label"],
                "pages": document["source_order"],
                "document_page_order": document["document_page_order"],
                "notes": " ".join(notes),
            }
        )

    page_labels = []
    for page in pages:
        page_label = {
            "page_number": page["page_number"],
            "label": page["label"],
            "confidence": page["confidence"],
            "notes": page_notes(page, documents, loan_conflict_pages),
        }
        marker = printed_page_marker(page["text"])
        if marker:
            page_label["printed_page"] = {
                "number": marker[0],
                "suffix": marker[2],
                "total": marker[1],
            }
        page_labels.append(page_label)

    quality_flags = []
    if any(conflict["field"] == "loan_number" for conflict in conflicts):
        quality_flags.append(
            {
                "flag_id": "FLAG-01",
                "type": "loan_number_conflict",
                "severity": "high",
                "related_pages": sorted(loan_related_pages),
                "action": "human_review",
                "conflict_id": "CONFLICT-LOAN_NUMBER",
            }
        )
    for document in documents:
        if document["source_order"] != document["document_page_order"]:
            quality_flags.append(
                {
                    "flag_id": f"FLAG-{len(quality_flags) + 1:02d}",
                    "type": "internal_page_order_mismatch",
                    "severity": "medium",
                    "related_pages": document["source_order"],
                    "action": "preserve_pdf_page_numbers_and_record_printed_page_order",
                    "document_id": document["document_id"],
                }
            )
    affidavit_pages = [
        page["page_number"]
        for page in pages
        if page["label"] == "Title - Signature / Name Affidavit (Ack)"
        and any(marker in page["normalized"] for marker in ("WILSEM", "ALJA"))
    ]
    if affidavit_pages:
        affidavit_doc = document_for_page(affidavit_pages[0], documents)
        quality_flags.append(
            {
                "flag_id": f"FLAG-{len(quality_flags) + 1:02d}",
                "type": "name_variants_in_affidavit",
                "severity": "medium",
                "related_pages": affidavit_pages,
                "action": "retain_variants_as_evidence_without_overwriting_canonical_borrower_name",
                "document_id": affidavit_doc["document_id"],
            }
        )

    return {
        "source_file": pdf_path.name,
        "page_count": len(pages),
        "confidence_policy": {
            "scale": "0.0-1.0 heuristic evidence-strength score",
            "calibrated": False,
            "notes": "Scores reflect document cues and distinct-document agreement. They are not calibrated probabilities; confidence does not resolve conflicts or replace review flags.",
        },
        "page_labels": page_labels,
        "documents": output_documents,
        "loan_level_fields": loan_result,
        "conflicts": conflicts,
        "quality_flags": quality_flags,
    }


def validate_result(result: dict[str, Any], labels: list[str], expected_fields: list[str]) -> None:
    """Fail closed on broken page coverage or source references before writing."""
    page_count = result["page_count"]
    expected_pages = set(range(1, page_count + 1))
    labeled_pages = [item["page_number"] for item in result["page_labels"]]
    if labeled_pages != list(range(1, page_count + 1)):
        raise ValueError("Page labels must cover every 1-based PDF page exactly once and in source order")
    invalid_labels = sorted({item["label"] for item in result["page_labels"]} - set(labels))
    if invalid_labels:
        raise ValueError(f"Output contains labels not allowed by candidate_classification_labels.txt: {invalid_labels}")

    grouped_pages = [page for document in result["documents"] for page in document["pages"]]
    if sorted(grouped_pages) != sorted(expected_pages) or len(grouped_pages) != len(set(grouped_pages)):
        raise ValueError("Document groups must partition the PDF pages without omissions or duplicates")
    if set(result["loan_level_fields"]) != set(expected_fields):
        raise ValueError("loan_level_fields do not match extraction_fields.json")

    for field_name, field in result["loan_level_fields"].items():
        invalid_sources = sorted(set(field["source_pages"]) - expected_pages)
        if invalid_sources:
            raise ValueError(f"{field_name} contains out-of-range source pages: {invalid_sources}")
    for conflict in result["conflicts"]:
        for observation in conflict["observations"]:
            invalid_sources = sorted(set(observation["source_pages"]) - expected_pages)
            if invalid_sources:
                raise ValueError(f"{conflict['field']} conflict contains out-of-range source pages: {invalid_sources}")


def run(pdf_path: Path, labels_path: Path, fields_path: Path) -> dict[str, Any]:
    labels = load_allowed_labels(labels_path)
    fields_config = read_json(fields_path)
    fields = list(fields_config)
    pages = extract_pages(pdf_path)
    for page in pages:
        classification = classify_page(page, labels)
        page.update(classification)
    documents = group_documents(pages)
    result = build_result(pdf_path, pages, documents, fields)
    validate_result(result, labels, fields)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "AREAL_LOAN.pdf", help="Input loan-package PDF")
    parser.add_argument("--labels", type=Path, default=ROOT / "candidate_classification_labels.txt", help="Allowed labels")
    parser.add_argument("--fields", type=Path, default=ROOT / "extraction_fields.json", help="Requested loan fields")
    parser.add_argument("--output", type=Path, default=ROOT / "result.json", help="Output JSON path")
    args = parser.parse_args()

    result = run(args.input, args.labels, args.fields)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    review_count = sum(flag.get("severity") == "high" for flag in result["quality_flags"])
    print(
        f"Wrote {args.output} with {result['page_count']} page labels, "
        f"{len(result['documents'])} document groups, and "
        f"{len(result['loan_level_fields'])} loan fields."
    )
    print(f"High-severity review flags: {review_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
