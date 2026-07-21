from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass

try:
    from .chunker import EXTRACTION_VERSION, _extract_layout_blocks
    from .layout import Block, BlockType
except ImportError:
    from chunker import EXTRACTION_VERSION, _extract_layout_blocks
    from layout import Block, BlockType


CHUNKING_VERSION = "semantic-v1"
DEFAULT_TARGET_CHARS = 700
DEFAULT_MAX_CHARS = 900
DEFAULT_OVERLAP_CHARS = 160
DEFAULT_TABLE_MAX_CHARS = 480

LINE_BREAK_HYPHEN = re.compile(r"(?<=[A-Za-z])-\n(?=[a-z])")
SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=["“”‘’(\[]*[A-Z0-9])')
REVISION_CODE = re.compile(r"^(?:[A-Z]{2,}-[A-Z0-9-]+-\d+|\d{3,}(?:\.\d+)+|\d{4})$")
NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+")
LETTERED_HEADING = re.compile(r"^[A-Z][.)]\s+")
MARKDOWN_SEPARATOR = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+$")
NUMERIC_TABLE_LINE = re.compile(r"(?:[$€£¥%]|\d)")


@dataclass(frozen=True, slots=True)
class SemanticUnit:
    text: str
    blocks: tuple[Block, ...]
    section_path: tuple[str, ...]
    unit_types: tuple[str, ...]

    @property
    def page_numbers(self):
        return tuple(sorted({block.page_number for block in self.blocks}))


def normalize_semantic_text(text, preserve_lines=False):
    text = str(text or "").replace("\u00ad", "")
    text = LINE_BREAK_HYPHEN.sub("", text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    separator = "\n" if preserve_lines else " "
    return separator.join(lines).strip()


def split_sentences(text):
    compact = " ".join(str(text or "").split())
    if not compact:
        return []
    return [part.strip() for part in SENTENCE_BOUNDARY.split(compact) if part.strip()]


def _split_words(text, max_chars):
    words = text.split()
    parts = []
    buffer = []
    for word in words:
        candidate = " ".join(buffer + [word])
        if buffer and len(candidate) > max_chars:
            parts.append(" ".join(buffer))
            buffer = [word]
        elif len(word) > max_chars:
            if buffer:
                parts.append(" ".join(buffer))
                buffer = []
            parts.extend(
                word[index:index + max_chars]
                for index in range(0, len(word), max_chars)
            )
        else:
            buffer.append(word)
    if buffer:
        parts.append(" ".join(buffer))
    return parts


def split_semantic_text(text, max_chars):
    if len(text) <= max_chars:
        return [text]

    sentences = split_sentences(text)
    parts = []
    buffer = []
    for sentence in sentences:
        if len(sentence) > max_chars:
            if buffer:
                parts.append(" ".join(buffer))
                buffer = []
            parts.extend(_split_words(sentence, max_chars))
            continue

        candidate = " ".join(buffer + [sentence])
        if buffer and len(candidate) > max_chars:
            parts.append(" ".join(buffer))
            buffer = [sentence]
        else:
            buffer.append(sentence)
    if buffer:
        parts.append(" ".join(buffer))
    return parts or _split_words(text, max_chars)


def _is_revision_heading(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return bool(lines) and any(REVISION_CODE.fullmatch(line) for line in lines)


def _heading_level(block, font_ranks):
    text = normalize_semantic_text(block.text)
    numbered = NUMBERED_HEADING.match(text)
    if numbered:
        return min(4, numbered.group(1).count(".") + 1)
    if LETTERED_HEADING.match(text):
        return 3
    if block.font_size is not None:
        size = round(block.font_size, 1)
        if size in font_ranks:
            return min(4, font_ranks.index(size) + 1)
    return 2 if block.is_bold else 1


def _body_font_sizes(blocks):
    weighted = defaultdict(lambda: defaultdict(int))
    for block in blocks:
        if block.block_type == BlockType.PARAGRAPH and block.font_size:
            weighted[block.page_number][round(block.font_size, 1)] += len(block.text)
    return {
        page_number: max(sizes.items(), key=lambda item: item[1])[0]
        for page_number, sizes in weighted.items()
        if sizes
    }


def _is_structural_heading(block, body_font_size):
    text = normalize_semantic_text(block.text)
    words = text.split()
    if not text or _is_revision_heading(block.text):
        return False
    if text.startswith(("•", "- ", "* ")):
        return False
    if block.font_size and body_font_size and block.font_size >= body_font_size * 1.15:
        return True
    if text.isupper() and len(words) <= 12:
        return True
    if (text.endswith(":") or NUMBERED_HEADING.match(text)) and len(words) <= 14:
        return True
    return len(words) <= 8 and len(text) <= 90 and ". " not in text


def _looks_tabular_text(text):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if len(lines) < 8:
        return False
    numeric_lines = sum(bool(NUMERIC_TABLE_LINE.search(line)) for line in lines)
    financial_markers = text.count("%") + text.count("$") + text.count("|")
    return numeric_lines >= len(lines) * 0.45 and financial_markers >= 4


def _split_table_text(text, max_chars):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    if len(text) <= max_chars:
        return ["\n".join(lines)]

    header = []
    body_start = 0
    if lines and lines[0].startswith("|"):
        header.append(lines[0])
        body_start = 1
        if len(lines) > 1 and MARKDOWN_SEPARATOR.fullmatch(lines[1]):
            header.append(lines[1])
            body_start = 2

    body = lines[body_start:]
    parts = []
    buffer = []
    for row in body:
        prefix = header if not buffer else []
        candidate = "\n".join(header + buffer + [row])
        if buffer and len(candidate) > max_chars:
            parts.append("\n".join(header + buffer))
            buffer = []
        if len("\n".join(header + [row])) > max_chars:
            parts.extend(split_semantic_text(row, max_chars - len("\n".join(header)) - 1))
        else:
            buffer.append(row)
    if buffer:
        parts.append("\n".join(header + buffer))
    return parts or ["\n".join(lines)]


def build_semantic_units(blocks, max_chars=DEFAULT_MAX_CHARS):
    body_sizes = _body_font_sizes(blocks)
    heading_sizes = sorted(
        {
            round(block.font_size, 1)
            for block in blocks
            if block.block_type == BlockType.HEADING and block.font_size is not None
        },
        reverse=True,
    )
    heading_stack = []
    raw_units = []

    for block in blocks:
        is_structural_heading = (
            block.block_type == BlockType.HEADING
            and _is_structural_heading(block, body_sizes.get(block.page_number))
        )
        if is_structural_heading:
            heading = normalize_semantic_text(block.text)
            if not heading or _is_revision_heading(block.text):
                continue
            level = _heading_level(block, heading_sizes)
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading))
            continue

        effective_type = (
            BlockType.PARAGRAPH
            if block.block_type == BlockType.HEADING
            else block.block_type
        )
        if effective_type == BlockType.PARAGRAPH and _looks_tabular_text(block.text):
            effective_type = BlockType.TABLE
        preserve_lines = effective_type in {BlockType.LIST, BlockType.TABLE}
        text = normalize_semantic_text(block.text, preserve_lines=preserve_lines)
        if not text:
            continue

        path = tuple(title for _, title in heading_stack)
        unit_type = effective_type.value
        heading_budget = len(path[-1]) + 2 if path else 0
        available_chars = max(20, max_chars - heading_budget)
        if effective_type == BlockType.TABLE:
            text_parts = _split_table_text(
                text,
                min(DEFAULT_TABLE_MAX_CHARS, available_chars),
            )
        else:
            text_parts = [text]

        raw_units.extend(
            SemanticUnit(
                text=text_part,
                blocks=(block,),
                section_path=path,
                unit_types=(unit_type,),
            )
            for text_part in text_parts
            if text_part
        )

    coalesced = []
    for unit in raw_units:
        if coalesced:
            previous = coalesced[-1]
            is_paragraph_continuation = (
                previous.section_path == unit.section_path
                and previous.unit_types == (BlockType.PARAGRAPH.value,)
                and unit.unit_types == (BlockType.PARAGRAPH.value,)
                and (
                    previous.text[-1:] not in ".!?;:)”\""
                    or unit.text[:1].islower()
                )
            )
            if is_paragraph_continuation:
                coalesced[-1] = SemanticUnit(
                    text=f"{previous.text} {unit.text}",
                    blocks=previous.blocks + unit.blocks,
                    section_path=previous.section_path,
                    unit_types=previous.unit_types,
                )
                continue
        coalesced.append(unit)

    units = []
    for unit in coalesced:
        if unit.unit_types == (BlockType.TABLE.value,):
            units.append(unit)
            continue
        heading_budget = len(unit.section_path[-1]) + 2 if unit.section_path else 0
        available_chars = max(20, max_chars - heading_budget)
        units.extend(
            SemanticUnit(
                text=part,
                blocks=unit.blocks,
                section_path=unit.section_path,
                unit_types=unit.unit_types,
            )
            for part in split_semantic_text(unit.text, available_chars)
        )
    return units


def _display_text(units, overlap_text=None):
    section_path = units[0].section_path if units else ()
    parts = []
    if section_path:
        parts.append(section_path[-1])
    if overlap_text:
        parts.append(overlap_text)
    parts.extend(unit.text for unit in units)
    return "\n\n".join(part for part in parts if part).strip()


def _embedding_text(units, display_text):
    section_path = units[0].section_path if units else ()
    if not section_path:
        return display_text
    breadcrumb = " > ".join(section_path)
    leaf = section_path[-1]
    body = display_text
    if body == leaf:
        body = ""
    elif body.startswith(f"{leaf}\n\n"):
        body = body[len(leaf) + 2:]
    return f"{breadcrumb}\n\n{body}".strip()


def _last_overlap_sentence(units, max_chars):
    if not units:
        return None
    sentences = split_sentences(units[-1].text)
    if not sentences:
        return None
    tail = sentences[-1]
    return tail if len(tail) <= max_chars else None


def _source_bboxes(units):
    seen = set()
    sources = []
    for unit in units:
        for block in unit.blocks:
            key = (block.page_number, tuple(block.bbox))
            if key in seen:
                continue
            seen.add(key)
            sources.append({
                "page_number": block.page_number,
                "bbox": list(block.bbox),
                "layout_type": block.metadata.get("layout_type", "text"),
                "layout_region": block.metadata.get("layout_region", "page"),
                "reading_order": block.metadata.get("reading_order"),
            })
    return sources


def _stable_semantic_id(index, source_document, source_fingerprint, section_path, text):
    identity = "\0".join(
        [
            source_fingerprint or "",
            source_document,
            str(index),
            " > ".join(section_path),
            text,
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _record_from_units(
    index,
    units,
    source_document,
    source_fingerprint,
    overlap_text=None,
):
    text = _display_text(units, overlap_text)
    section_path = units[0].section_path if units else ()
    page_numbers = sorted({page for unit in units for page in unit.page_numbers})
    semantic_types = tuple(dict.fromkeys(kind for unit in units for kind in unit.unit_types))
    block_types = list(semantic_types)
    if section_path and "heading" not in block_types:
        block_types.insert(0, "heading")
    embedding_text = _embedding_text(units, text)
    return {
        "chunk_id": _stable_semantic_id(
            index,
            source_document,
            source_fingerprint,
            section_path,
            text,
        ),
        "chunk_index": index,
        "text": text,
        "embedding_text": embedding_text,
        "source_document": source_document,
        "page_number": page_numbers[0] if page_numbers else None,
        "page_start": page_numbers[0] if page_numbers else None,
        "page_end": page_numbers[-1] if page_numbers else None,
        "page_numbers": page_numbers,
        "section_title": section_path[-1] if section_path else None,
        "section_path": list(section_path),
        "block_types": block_types,
        "semantic_unit_types": list(semantic_types),
        "source_bboxes": _source_bboxes(units),
        "overlap_with_previous_chars": len(overlap_text or ""),
        "source_fingerprint": source_fingerprint,
        "extraction_version": EXTRACTION_VERSION,
        "chunking_version": CHUNKING_VERSION,
    }


def semantic_chunk_pages(
    pages,
    source_document,
    target_chars=DEFAULT_TARGET_CHARS,
    max_chars=DEFAULT_MAX_CHARS,
    overlap_chars=DEFAULT_OVERLAP_CHARS,
    source_fingerprint=None,
):
    if not 0 < target_chars <= max_chars:
        raise ValueError("target_chars must be positive and no greater than max_chars")

    blocks = _extract_layout_blocks(pages)
    units = build_semantic_units(blocks, max_chars=max_chars)
    groups = []
    buffer = []

    def flush():
        if buffer:
            groups.append(tuple(buffer))
            buffer.clear()

    for unit in units:
        if buffer and unit.section_path != buffer[0].section_path:
            flush()

        candidate = buffer + [unit]
        candidate_text = _display_text(candidate)
        current_text = _display_text(buffer) if buffer else ""
        if buffer and (len(candidate_text) > max_chars or len(current_text) >= target_chars):
            flush()
        buffer.append(unit)
    flush()

    records = []
    previous_group = None
    for group in groups:
        overlap_text = None
        if previous_group and previous_group[0].section_path == group[0].section_path:
            candidate_overlap = _last_overlap_sentence(previous_group, overlap_chars)
            if candidate_overlap and len(_display_text(group, candidate_overlap)) <= max_chars:
                overlap_text = candidate_overlap
        records.append(
            _record_from_units(
                len(records),
                group,
                source_document,
                source_fingerprint,
                overlap_text=overlap_text,
            )
        )
        previous_group = group

    return records
