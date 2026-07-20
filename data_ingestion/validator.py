import argparse
import copy
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_MAX_CHARS = 1000
DEFAULT_EMBEDDING_DIM = 384

REQUIRED_FIELDS = {
    "chunk_index",
    "chunk_id",
    "text",
    "source_document",
    "page_number",
    "page_start",
    "page_end",
    "page_numbers",
    "section_title",
    "block_types",
    "source_fingerprint",
    "extraction_version",
}

CONTROL_CHAR = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HYPHENATED_LINE_BREAK = re.compile(r"(?<=[A-Za-z])-\s*\n\s*(?=[a-z])")
EXCESSIVE_WHITESPACE = re.compile(r"[ \t]{2,}")
REVISION_LINE = re.compile(
    r"^(?:\d{3,}(?:\.\d+)+|[A-Z]{2}-[A-Z0-9-]+-\d+|\d{4}|1\.\d+)$"
)
MOSTLY_CODE = re.compile(r"^[A-Z0-9.\-\s/]+$")
SENTENCE_START = re.compile(r"^[A-Z][a-z]+(?:\s+[a-z]+){0,3}\s+[a-z]+\b")


def read_jsonl(path):
    records = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            record["_line_number"] = line_number
            records.append(record)
    return records


def normalize_text(text):
    text = CONTROL_CHAR.sub(" ", str(text or ""))
    text = HYPHENATED_LINE_BREAK.sub("", text)
    lines = [EXCESSIVE_WHITESPACE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def is_revision_code_section(value):
    if not value:
        return False

    lines = [line.strip() for line in str(value).splitlines() if line.strip()]
    if not lines:
        return False

    if any(REVISION_LINE.fullmatch(line) for line in lines):
        return True

    compact = " ".join(lines)
    if MOSTLY_CODE.fullmatch(compact):
        letters = sum(char.isalpha() for char in compact)
        digits = sum(char.isdigit() for char in compact)
        separators = sum(char in ".-/ " for char in compact)
        return digits >= letters and digits + separators >= max(6, len(compact) * 0.6)

    return False


def likely_column_interleaved(text):
    compact = " ".join(str(text or "").split())
    if not compact:
        return False

    lower = compact.lower()
    suspicious_fragments = (
        "for may grant",
        "risk of a margin call. use of features the loan",
        "entails additional risks. short selling outside the core account",
        "while fidelity stitute payments",
    )
    if any(fragment in lower for fragment in suspicious_fragments):
        return True

    # A weak grammar smell that catches text starting mid-sentence and then
    # rapidly jumping topics, common in row-wise extraction of visual columns.
    starts_mid_sentence = not SENTENCE_START.match(compact[:80])
    many_sentence_breaks = compact.count(". ") >= 4
    many_short_phrases = sum(1 for part in compact.split(",") if len(part.split()) <= 3) >= 5
    return starts_mid_sentence and many_sentence_breaks and many_short_phrases


def warning_counts(records):
    counts = Counter()
    for record in records:
        for warning in record.get("validation_warnings", []):
            counts[warning] += 1
    return dict(sorted(counts.items()))


def validate_records(records, max_chars=DEFAULT_MAX_CHARS, embedding_dim=DEFAULT_EMBEDDING_DIM):
    text_counts = Counter(record.get("text", "") for record in records)
    ids = Counter(record.get("chunk_id") for record in records)
    indexes = [record.get("chunk_index") for record in records]
    validated_records = []
    dropped_records = []
    hard_errors = []

    expected_indexes = list(range(len(records)))
    if indexes != expected_indexes:
        hard_errors.append("chunk_index values are not contiguous")

    for record in records:
        cleaned = copy.deepcopy(record)
        warnings = []
        errors = []

        missing = sorted(REQUIRED_FIELDS - set(record))
        if missing:
            errors.append(f"missing fields: {', '.join(missing)}")

        text = str(record.get("text", ""))
        cleaned_text = normalize_text(text)
        if not cleaned_text:
            errors.append("empty text")

        if len(cleaned_text) > max_chars:
            errors.append(f"text length exceeds {max_chars}")

        if CONTROL_CHAR.search(text):
            warnings.append("control_characters_removed")

        if HYPHENATED_LINE_BREAK.search(text):
            warnings.append("hyphenated_line_breaks_fixed")

        if text_counts[text] > 1:
            warnings.append("duplicate_text")

        section_title = record.get("section_title")
        if is_revision_code_section(section_title):
            warnings.append("revision_code_section_title")
            cleaned["section_title"] = None

        block_types = record.get("block_types") or []
        is_heading_only = block_types == ["heading"]
        if is_heading_only:
            warnings.append("heading_only")

        if cleaned_text.count("|") > 20:
            warnings.append("pipe_heavy")

        if likely_column_interleaved(cleaned_text):
            warnings.append("likely_column_interleaved")

        page_start = record.get("page_start")
        page_end = record.get("page_end")
        if page_start is not None and page_end is not None and page_start > page_end:
            errors.append("page_start is greater than page_end")

        page_numbers = record.get("page_numbers")
        if page_numbers and page_start is not None and page_end is not None:
            if min(page_numbers) != page_start or max(page_numbers) != page_end:
                warnings.append("page_range_mismatch")

        embedding = record.get("embedding")
        if embedding is not None and len(embedding) != embedding_dim:
            errors.append(f"embedding length is not {embedding_dim}")

        if record.get("chunking_version") == "semantic-v1":
            semantic_fields = {
                "embedding_text",
                "section_path",
                "semantic_unit_types",
                "token_count",
                "embedding_max_tokens",
            }
            missing_semantic = sorted(semantic_fields - set(record))
            if missing_semantic:
                errors.append(
                    f"missing semantic fields: {', '.join(missing_semantic)}"
                )
            if not str(record.get("embedding_text", "")).strip():
                errors.append("empty embedding_text")
            token_count = record.get("token_count")
            token_limit = record.get("embedding_max_tokens")
            if (
                isinstance(token_count, int)
                and isinstance(token_limit, int)
                and token_count > token_limit
            ):
                errors.append("embedding input exceeds model token limit")

        if ids[record.get("chunk_id")] > 1:
            errors.append("chunk_id is not unique")

        cleaned["text"] = cleaned_text
        cleaned["validation_warnings"] = warnings
        cleaned["validation_errors"] = errors

        drop_reason = None
        if text_counts[text] > 1 and text in {item.get("text") for item in validated_records}:
            drop_reason = "duplicate_text"
        elif is_heading_only and is_revision_code_section(section_title):
            drop_reason = "revision_code_heading_only"

        if drop_reason:
            dropped = copy.deepcopy(cleaned)
            dropped["drop_reason"] = drop_reason
            dropped_records.append(dropped)
            continue

        validated_records.append(cleaned)

    hard_error_count = sum(len(record.get("validation_errors", [])) for record in validated_records)
    hard_error_count += len(hard_errors)

    return {
        "records": validated_records,
        "dropped_records": dropped_records,
        "summary": {
            "input_records": len(records),
            "validated_records": len(validated_records),
            "dropped_records": len(dropped_records),
            "hard_errors": hard_error_count,
            "warnings": sum(len(record.get("validation_warnings", [])) for record in validated_records),
            "warning_counts": warning_counts(validated_records),
            "global_errors": hard_errors,
        },
    }


def print_report(result):
    summary = result["summary"]
    print(f"input records: {summary['input_records']}")
    print(f"validated records: {summary['validated_records']}")
    print(f"dropped records: {summary['dropped_records']}")
    print(f"hard errors: {summary['hard_errors']}")
    print(f"warnings: {summary['warnings']}")
    for name, count in summary["warning_counts"].items():
        print(f"warning {name}: {count}")
    for error in summary["global_errors"]:
        print(f"error: {error}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate VeriFi ingestion chunks.")
    parser.add_argument("jsonl_path", nargs="?", default="output/chunks.jsonl")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args(argv)

    records = read_jsonl(args.jsonl_path)
    result = validate_records(records, args.max_chars, args.embedding_dim)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)

    if result["summary"]["hard_errors"]:
        return 1
    if result["summary"]["warnings"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
