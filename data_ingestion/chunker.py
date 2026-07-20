import hashlib
import re

try:
    from .layout import Block, BlockType, build_sections
except ImportError:
    from layout import Block, BlockType, build_sections


EXTRACTION_VERSION = "layout-v2"


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\x07", " ")
    # Clean multiple spaces on each line, but keep newlines
    lines = []
    for line in text.splitlines():
        cleaned_line = " ".join(line.split())
        if cleaned_line:
            lines.append(cleaned_line)
    return "\n".join(lines)


def _hard_split(text, max_chars):
    return [
        text[index:index + max_chars]
        for index in range(0, len(text), max_chars)
        if text[index:index + max_chars]
    ]


def chunk_text(text, max_chars=1000, overlap=100):
    if not text:
        return []

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    text = clean_text(text)
    # Tokenize: words and whitespace sequences
    tokens = re.split(r'(\s+)', text)
    tokens = [t for t in tokens if t]

    chunks = []
    start_idx = 0

    while start_idx < len(tokens):
        current_len = 0
        end_idx = start_idx

        while end_idx < len(tokens):
            t = tokens[end_idx]
            if end_idx == start_idx and t.isspace():
                start_idx += 1
                end_idx += 1
                continue

            if current_len + len(t) > max_chars and current_len > 0:
                break

            current_len += len(t)
            end_idx += 1

        if end_idx == start_idx and len(tokens[start_idx]) > max_chars:
            chunks.extend(_hard_split(tokens[start_idx], max_chars))
            start_idx += 1
            continue

        chunk_tokens = tokens[start_idx:end_idx]
        while chunk_tokens and chunk_tokens[-1].isspace():
            chunk_tokens.pop()

        chunk_text_str = "".join(chunk_tokens)
        if chunk_text_str:
            if len(chunk_text_str) > max_chars:
                chunks.extend(_hard_split(chunk_text_str, max_chars))
            else:
                chunks.append(chunk_text_str)

        if end_idx >= len(tokens):
            break

        overlap_chars = 0
        overlap_start = end_idx

        while overlap_start > start_idx:
            t = tokens[overlap_start - 1]
            if overlap_chars + len(t) > overlap:
                break
            overlap_chars += len(t)
            overlap_start -= 1

        if overlap_start == end_idx:
            start_idx = end_idx
        else:
            start_idx = overlap_start

    return chunks


def _split_table_text(text, max_chars, overlap):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    chunks = []
    buffer = []

    def flush():
        if not buffer:
            return
        chunk = "\n".join(buffer).strip()
        if len(chunk) <= max_chars:
            chunks.append(chunk)
        else:
            chunks.extend(chunk_text(chunk, max_chars, overlap))
        buffer.clear()

    for line in lines:
        candidate = "\n".join(buffer + [line]).strip()
        if buffer and len(candidate) > max_chars:
            flush()
        if len(line) > max_chars:
            chunks.extend(chunk_text(line, max_chars, overlap))
        else:
            buffer.append(line)

    flush()
    return chunks


def _block_from_dict(block, default_page_number):
    if isinstance(block, Block):
        return block

    return Block(
        text=block.get("text", ""),
        page_number=block.get("page_number", default_page_number),
        bbox=tuple(block.get("bbox", (0.0, 0.0, 0.0, 0.0))),
        block_type=block.get("block_type", BlockType.PARAGRAPH),
        font_size=block.get("font_size"),
        is_bold=block.get("is_bold", False),
        metadata=block.get("metadata", {}),
    )


def _extract_layout_blocks(pages):
    blocks = []
    for page in pages:
        page_number = page["page_number"]
        for block in page.get("blocks", []):
            parsed = _block_from_dict(block, page_number)
            if parsed.text:
                blocks.append(parsed)
    return blocks


def _stable_chunk_id(
    chunk_index,
    source_document,
    source_fingerprint,
    page_numbers,
    section_title,
    text,
):
    identity = "\0".join(
        [
            source_fingerprint or "",
            source_document,
            str(chunk_index),
            ",".join(str(page_number) for page_number in page_numbers),
            section_title or "",
            text,
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _chunk_metadata(
    chunk_index,
    text,
    source_document,
    blocks,
    section_title,
    source_fingerprint=None,
):
    page_numbers = tuple(
        sorted({block.page_number for block in blocks if block.page_number})
    )
    block_types = tuple(
        dict.fromkeys(block.block_type.value for block in blocks)
    )
    page_start = page_numbers[0] if page_numbers else None
    page_end = page_numbers[-1] if page_numbers else None
    return {
        "chunk_id": _stable_chunk_id(
            chunk_index,
            source_document,
            source_fingerprint,
            page_numbers,
            section_title,
            text,
        ),
        "chunk_index": chunk_index,
        "text": text,
        "source_document": source_document,
        "page_number": page_start,
        "page_start": page_start,
        "page_end": page_end,
        "page_numbers": list(page_numbers),
        "section_title": section_title,
        "block_types": list(block_types),
        "source_fingerprint": source_fingerprint,
        "extraction_version": EXTRACTION_VERSION,
    }


def _add_block_chunks(
    records,
    chunk_index,
    block,
    source_document,
    section_title,
    max_chars,
    overlap,
    source_fingerprint,
):
    splitter = _split_table_text if block.block_type == BlockType.TABLE else chunk_text
    for text_part in splitter(block.text, max_chars, overlap):
        records.append(
            _chunk_metadata(
                chunk_index,
                text_part,
                source_document,
                (block,),
                section_title,
                source_fingerprint,
            )
        )
        chunk_index += 1
    return chunk_index


def _structured_chunk_records(
    blocks,
    source_document,
    max_chars,
    overlap,
    source_fingerprint=None,
):
    records = []
    chunk_index = 0

    for section in build_sections(blocks):
        buffer = []

        def flush_buffer():
            nonlocal chunk_index
            if not buffer:
                return
            text = "\n\n".join(block.text for block in buffer).strip()
            if text:
                records.append(
                    _chunk_metadata(
                        chunk_index,
                        text,
                        source_document,
                        tuple(buffer),
                        section.title,
                        source_fingerprint,
                    )
                )
                chunk_index += 1
            buffer.clear()

        for block in section.blocks:
            candidate_blocks = buffer + [block]
            candidate_text = "\n\n".join(
                item.text for item in candidate_blocks
            ).strip()

            if len(candidate_text) <= max_chars or not buffer:
                if len(block.text) > max_chars:
                    flush_buffer()
                    chunk_index = _add_block_chunks(
                        records,
                        chunk_index,
                        block,
                        source_document,
                        section.title,
                        max_chars,
                        overlap,
                        source_fingerprint,
                    )
                else:
                    buffer.append(block)
                continue

            flush_buffer()
            if len(block.text) > max_chars:
                chunk_index = _add_block_chunks(
                    records,
                    chunk_index,
                    block,
                    source_document,
                    section.title,
                    max_chars,
                    overlap,
                    source_fingerprint,
                )
            else:
                buffer.append(block)

        flush_buffer()

    return records


def chunk_pages(
    pages,
    source_document,
    max_chars=1000,
    overlap=100,
    source_fingerprint=None,
):
    layout_blocks = _extract_layout_blocks(pages)
    if layout_blocks:
        return _structured_chunk_records(
            layout_blocks,
            source_document,
            max_chars,
            overlap,
            source_fingerprint,
        )

    records = []
    chunk_index = 0

    for page in pages:
        page_chunks = chunk_text(
            page["text"],
            max_chars=max_chars,
            overlap=overlap
        )

        for chunk in page_chunks:
            records.append({
                "chunk_index": chunk_index,
                "text": chunk,
                "source_document": source_document,
                "page_number": page["page_number"]
            })

            chunk_index += 1

    return records
