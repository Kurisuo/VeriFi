import math
import re
from collections import defaultdict

import fitz

try:
    from .layout import Block, BlockType, PageLayout, build_sections
except ImportError:
    from layout import Block, BlockType, PageLayout, build_sections


CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
NON_WORD = re.compile(r"[^\w\s]", flags=re.UNICODE)
PAGE_NUMBER = re.compile(
    r"^(?:page\s+)?\d+(?:\s+(?:of|/)\s+\d+)?$",
    flags=re.IGNORECASE,
)
DOCUMENT_FOOTER = re.compile(
    r"^(?:\d+\s+)?fidelity account(?:®)? customer agreement(?:\s+\d+)?$",
    flags=re.IGNORECASE,
)
LIST_MARKER = re.compile(r"^\s*(?:[-*\u2022]|\(?[a-zA-Z0-9]{1,3}[.)])\s+")
SECTION_NUMBER = re.compile(r"^\s*(?:\d+(?:\.\d+)*|[IVXLC]+)[.)]?\s+\S+")


def clean_extracted_text(text):
    """Remove PDF control glyphs without flattening meaningful line breaks."""
    if not text:
        return ""

    text = CONTROL_CHARACTERS.sub(" ", str(text)).replace("\t", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def is_inside(block_bbox, table_bbox, tolerance=5):
    bx0, by0, bx1, by1 = block_bbox
    tx0, ty0, tx1, ty1 = table_bbox
    cx = (bx0 + bx1) / 2
    cy = (by0 + by1) / 2
    return (
        tx0 - tolerance <= cx <= tx1 + tolerance
        and ty0 - tolerance <= cy <= ty1 + tolerance
    )


def _intersection_ratio(block_bbox, table_bbox):
    bx0, by0, bx1, by1 = block_bbox
    tx0, ty0, tx1, ty1 = table_bbox
    width = max(0.0, min(bx1, tx1) - max(bx0, tx0))
    height = max(0.0, min(by1, ty1) - max(by0, ty0))
    block_area = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    return (width * height / block_area) if block_area else 0.0


def _is_table_text(block_bbox, table_bbox):
    return is_inside(block_bbox, table_bbox) or _intersection_ratio(
        block_bbox, table_bbox
    ) >= 0.5


def _format_table_cell(cell):
    text = clean_extracted_text(cell).replace("\n", " ")
    return text.replace("|", r"\|")


def _looks_like_header(rows):
    if len(rows) < 2:
        return False

    header = rows[0]
    nonempty = [cell for cell in header if cell]
    return (
        len(nonempty) >= max(1, math.ceil(len(header) / 2))
        and max((len(cell) for cell in nonempty), default=0) <= 100
    )


def format_markdown_table(raw_table):
    if not raw_table:
        return ""

    rows = []
    for raw_row in raw_table:
        row = [_format_table_cell(cell) for cell in raw_row]
        if any(row):
            rows.append(row)

    if not rows:
        return ""

    markdown_lines = ["| " + " | ".join(row) + " |" for row in rows]
    if _looks_like_header(rows):
        markdown_lines.insert(
            1, "| " + " | ".join("---" for _ in rows[0]) + " |"
        )
    return "\n".join(markdown_lines)


def _normalized_cell_text(value):
    return " ".join(clean_extracted_text(value).lower().split())


def _is_valid_table_candidate(table, page_width, page_height):
    """Reject decorative boxes that PyMuPDF sometimes reports as tables."""
    rows = table.extract()
    if not rows:
        return False

    cells = [
        _normalized_cell_text(cell)
        for row in rows
        for cell in row
        if _normalized_cell_text(cell)
    ]
    if len(cells) < 4:
        return False

    unique_cells = set(cells)
    duplicate_long_cells = len(cells) - len(unique_cells)
    longest_cell = max((len(cell) for cell in cells), default=0)
    x0, y0, x1, y1 = table.bbox
    page_area = max(1.0, page_width * page_height)
    area_ratio = max(0.0, x1 - x0) * max(0.0, y1 - y0) / page_area

    # Decorative disclosure boxes typically appear as a huge 2-3 row table
    # whose cells repeat the same complete passage. Genuine tables have more
    # populated cells and substantially more distinct row-level content.
    if len(rows) <= 3 and area_ratio >= 0.15:
        return False
    if (
        len(rows) <= 3
        and duplicate_long_cells
        and longest_cell >= 300
        and area_ratio >= 0.10
    ):
        return False
    if area_ratio >= 0.25 and len(unique_cells) <= 3:
        return False

    return True


def _header_footer_signature(text):
    normalized = clean_extracted_text(text).lower()
    normalized = re.sub(r"\d+", "#", normalized)
    normalized = re.sub(r"^\s*#\s+", "", normalized)
    normalized = re.sub(r"\s+#\s*$", "", normalized)
    normalized = NON_WORD.sub(" ", normalized)
    return " ".join(normalized.split())


def _is_margin_block(bbox, page_height):
    _, y0, _, y1 = bbox
    return y1 <= page_height * 0.10 or y0 >= page_height * 0.90


def _repeated_margin_signatures(raw_pages):
    pages_by_signature = defaultdict(set)

    for raw_page in raw_pages:
        page_number = raw_page["page_number"]
        page_height = raw_page["height"]
        for block in raw_page["blocks"]:
            text = block["text"]
            if (
                len(text) <= 200
                and _is_margin_block(block["bbox"], page_height)
            ):
                signature = _header_footer_signature(text)
                if signature:
                    pages_by_signature[signature].add(page_number)

    page_count = len(raw_pages)
    if page_count < 2:
        return set()

    minimum_repetitions = max(2, math.ceil(page_count * 0.30))
    return {
        signature
        for signature, page_numbers in pages_by_signature.items()
        if len(page_numbers) >= minimum_repetitions
    }


def is_header_footer(
    text,
    bbox,
    page_height=792,
    repeated_signatures=None,
):
    """Return True only for page numbers or document-wide repeated margin text."""
    text_clean = clean_extracted_text(text)
    if not text_clean:
        return True

    if not _is_margin_block(bbox, page_height):
        return False

    if PAGE_NUMBER.fullmatch(" ".join(text_clean.split())):
        return True

    if DOCUMENT_FOOTER.fullmatch(" ".join(text_clean.split())):
        return True

    repeated_signatures = repeated_signatures or set()
    return _header_footer_signature(text_clean) in repeated_signatures


def _sort_rows(blocks, tolerance=4.0):
    """Sort top-to-bottom, then left-to-right for blocks sharing a row."""
    rows = []
    for block in sorted(blocks, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        y0 = block["bbox"][1]
        for row in rows:
            if abs(y0 - row["y0"]) <= tolerance:
                row["blocks"].append(block)
                row["y0"] = min(row["y0"], y0)
                break
        else:
            rows.append({"y0": y0, "blocks": [block]})

    ordered = []
    for row in sorted(rows, key=lambda item: item["y0"]):
        ordered.extend(sorted(row["blocks"], key=lambda item: item["bbox"][0]))
    return ordered


def _layout_weight(block):
    return max(1, int(block.get("layout_weight", 1)))


def _find_column_gutter(blocks, page_width):
    """Find the strongest persistent vertical whitespace gutter."""
    if len(blocks) < 4:
        return None

    x_min = min(block["bbox"][0] for block in blocks)
    x_max = max(block["bbox"][2] for block in blocks)
    region_width = x_max - x_min
    if region_width < page_width * 0.25:
        return None

    step = max(1.5, page_width / 320.0)
    positions = []
    x = x_min + step
    while x < x_max - step:
        left_weight = sum(
            _layout_weight(block)
            for block in blocks
            if block["bbox"][2] <= x + 2.0
        )
        right_weight = sum(
            _layout_weight(block)
            for block in blocks
            if block["bbox"][0] >= x - 2.0
        )
        spanning = sum(
            1
            for block in blocks
            if block["bbox"][0] < x - 2.0 and block["bbox"][2] > x + 2.0
        )
        allowed_spanning = max(1, math.floor(len(blocks) * 0.06))
        if left_weight >= 3 and right_weight >= 3 and spanning <= allowed_spanning:
            positions.append(x)
        x += step

    if not positions:
        return None

    runs = []
    run = [positions[0]]
    for position in positions[1:]:
        if position - run[-1] <= step * 1.6:
            run.append(position)
        else:
            runs.append(run)
            run = [position]
    runs.append(run)

    candidates = []
    for run in runs:
        width = run[-1] - run[0] + step
        if width < max(8.0, page_width * 0.012):
            continue
        midpoint = (run[0] + run[-1]) / 2
        left_weight = sum(
            _layout_weight(block)
            for block in blocks
            if block["bbox"][2] <= midpoint + 2.0
        )
        right_weight = sum(
            _layout_weight(block)
            for block in blocks
            if block["bbox"][0] >= midpoint - 2.0
        )
        balance = min(left_weight, right_weight) / max(left_weight, right_weight)
        candidates.append((width * (0.5 + balance), midpoint))

    return max(candidates, default=(0.0, None))[1]


def _sort_region(blocks, page_width):
    """Recursively order one-, two-, or multi-column layout regions."""
    if len(blocks) < 2:
        return list(blocks)

    gutter = _find_column_gutter(blocks, page_width)
    if gutter is None:
        return _sort_rows(blocks)

    left = [block for block in blocks if block["bbox"][2] <= gutter + 2.0]
    right = [block for block in blocks if block["bbox"][0] >= gutter - 2.0]
    spanning = [block for block in blocks if block not in left and block not in right]

    if not left or not right:
        return _sort_rows(blocks)

    if not spanning:
        return _sort_region(left, page_width) + _sort_region(right, page_width)

    ordered = []
    remaining_left = left
    remaining_right = right
    for spanning_block in sorted(spanning, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        cutoff = spanning_block["bbox"][1]
        preceding_left = [block for block in remaining_left if block["bbox"][1] < cutoff]
        preceding_right = [block for block in remaining_right if block["bbox"][1] < cutoff]
        remaining_left = [block for block in remaining_left if block not in preceding_left]
        remaining_right = [block for block in remaining_right if block not in preceding_right]
        ordered.extend(_sort_region(preceding_left, page_width))
        ordered.extend(_sort_region(preceding_right, page_width))
        ordered.append(spanning_block)

    ordered.extend(_sort_region(remaining_left, page_width))
    ordered.extend(_sort_region(remaining_right, page_width))
    return ordered


def order_page_blocks(blocks, page_width):
    """Order mixed full-width and multi-column blocks."""
    return _sort_region(blocks, page_width)


def _classify_block(text, is_table=False, font_size=None, body_font_size=None, is_bold=False):
    if is_table:
        return BlockType.TABLE

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and all(LIST_MARKER.match(line) for line in lines):
        return BlockType.LIST

    compact_text = " ".join(lines)
    if not compact_text:
        return BlockType.PARAGRAPH

    is_short = len(compact_text) <= 160 and len(lines) <= 3
    larger_than_body = (
        font_size is not None
        and body_font_size is not None
        and font_size >= body_font_size * 1.18
    )
    has_heading_shape = (
        compact_text.isupper()
        or SECTION_NUMBER.match(compact_text)
        or compact_text.endswith(":")
    )
    ends_like_sentence = compact_text.endswith((".", "?", "!"))
    if is_short and (larger_than_body or has_heading_shape or is_bold) and not ends_like_sentence:
        return BlockType.HEADING

    return BlockType.PARAGRAPH


def _span_is_bold(span):
    font_name = span.get("font", "").lower()
    return "bold" in font_name or bool(span.get("flags", 0) & 16)


def _text_lines_from_dict(page):
    lines_out = []
    for block_index, raw_block in enumerate(page.get_text("dict").get("blocks", [])):
        if raw_block.get("type") != 0:
            continue

        for line_index, line in enumerate(raw_block.get("lines", [])):
            raw_parts = []
            font_sizes = []
            bold_chars = 0
            total_chars = 0
            for span in line.get("spans", []):
                raw_text = str(span.get("text", ""))
                text = clean_extracted_text(raw_text)
                if not text:
                    continue
                raw_parts.append(raw_text)
                char_count = len(text)
                total_chars += char_count
                font_sizes.extend([float(span.get("size", 0.0))] * max(1, char_count))
                if _span_is_bold(span):
                    bold_chars += char_count
            text = clean_extracted_text("".join(raw_parts))
            if text:
                font_size = max(font_sizes) if font_sizes else None
                lines_out.append(
                {
                    "bbox": tuple(float(value) for value in line["bbox"]),
                    "text": text,
                    "is_table": False,
                    "font_size": font_size,
                    "is_bold": bool(total_chars and bold_chars / total_chars >= 0.45),
                    "source_block_index": block_index,
                    "source_line_index": line_index,
                }
            )
    return lines_out


def _can_merge_lines(previous, current):
    if previous.get("is_table") or current.get("is_table"):
        return False
    if previous.get("layout_region") != current.get("layout_region"):
        return False
    if previous.get("source_block_index") != current.get("source_block_index"):
        return False
    if previous.get("is_bold") != current.get("is_bold"):
        return False

    px0, py0, px1, py1 = previous["bbox"]
    cx0, cy0, cx1, cy1 = current["bbox"]
    line_height = max(1.0, py1 - py0, cy1 - cy0)
    return (
        cy0 >= py0 - 2.0
        and cy0 - py1 <= max(8.0, line_height * 0.9)
        and abs(cx0 - px0) <= 28.0
    )


def _merge_ordered_lines(items):
    blocks = []
    for item in items:
        if item.get("is_table"):
            blocks.append(dict(item))
            continue

        if blocks and _can_merge_lines(blocks[-1], item):
            previous = blocks[-1]
            previous["text"] = f'{previous["text"]}\n{item["text"]}'
            previous["bbox"] = (
                min(previous["bbox"][0], item["bbox"][0]),
                min(previous["bbox"][1], item["bbox"][1]),
                max(previous["bbox"][2], item["bbox"][2]),
                max(previous["bbox"][3], item["bbox"][3]),
            )
            previous["font_size"] = max(
                previous.get("font_size") or 0.0,
                item.get("font_size") or 0.0,
            ) or None
            continue

        blocks.append(dict(item))

    for reading_order, block in enumerate(blocks):
        block["reading_order"] = reading_order
    return blocks


def _expand_layout_items(items):
    expanded = []
    for item in items:
        expanded.extend(item.get("children", [item]))
    return expanded


def _extract_raw_page(page, page_number):
    page_width = float(page.rect.width)
    page_height = float(page.rect.height)
    tables = list(page.find_tables().tables)
    valid_tables = [
        table
        for table in tables
        if _is_valid_table_candidate(table, page_width, page_height)
    ]
    rejected_tables = [table for table in tables if table not in valid_tables]
    valid_table_bboxes = [tuple(table.bbox) for table in valid_tables]
    text_lines = _text_lines_from_dict(page)

    outside_lines = []
    rejected_region_lines = defaultdict(list)
    for line in text_lines:
        bbox = line["bbox"]
        if any(_is_table_text(bbox, table_bbox) for table_bbox in valid_table_bboxes):
            continue

        matching_regions = [
            (region_index, tuple(table.bbox))
            for region_index, table in enumerate(rejected_tables)
            if _is_table_text(bbox, tuple(table.bbox))
        ]
        if matching_regions:
            region_index, _ = min(
                matching_regions,
                key=lambda item: (item[1][2] - item[1][0]) * (item[1][3] - item[1][1]),
            )
            line["layout_region"] = f"boxed-{region_index}"
            line["layout_type"] = "boxed_region"
            rejected_region_lines[region_index].append(line)
        else:
            line["layout_region"] = "page"
            line["layout_type"] = "text"
            outside_lines.append(line)

    layout_items = list(outside_lines)
    for region_index, table in enumerate(rejected_tables):
        region_lines = rejected_region_lines.get(region_index, [])
        if not region_lines:
            continue
        ordered_children = order_page_blocks(region_lines, page_width)
        layout_items.append(
            {
                "bbox": tuple(float(value) for value in table.bbox),
                "children": ordered_children,
                "layout_weight": len(ordered_children),
                "layout_region": f"boxed-{region_index}",
                "layout_type": "boxed_region",
            }
        )

    for table_index, table in enumerate(valid_tables):
        table_text = format_markdown_table(table.extract())
        if table_text:
            layout_items.append(
                {
                    "bbox": tuple(float(value) for value in table.bbox),
                    "text": table_text,
                    "is_table": True,
                    "font_size": None,
                    "is_bold": False,
                    "layout_region": f"table-{table_index}",
                    "layout_type": "table",
                }
            )

    ordered_items = order_page_blocks(layout_items, page_width)
    blocks = _merge_ordered_lines(_expand_layout_items(ordered_items))

    return {
        "page_number": page_number,
        "width": page_width,
        "height": page_height,
        "blocks": blocks,
    }


def _body_font_size(raw_pages):
    weighted_sizes = defaultdict(int)
    for raw_page in raw_pages:
        for block in raw_page["blocks"]:
            if block["is_table"] or _is_margin_block(block["bbox"], raw_page["height"]):
                continue
            font_size = block.get("font_size")
            if font_size:
                weighted_sizes[round(font_size, 1)] += len(block["text"])

    if not weighted_sizes:
        return None
    return max(weighted_sizes.items(), key=lambda item: item[1])[0]


def _page_layout_from_raw(raw_page, repeated_signatures=None, body_font_size=None):
    blocks = [
        block
        for block in raw_page["blocks"]
        if not is_header_footer(
            block["text"],
            block["bbox"],
            page_height=raw_page["height"],
            repeated_signatures=repeated_signatures,
        )
    ]
    ordered = order_page_blocks(blocks, raw_page["width"])
    layout_blocks = tuple(
        Block(
            text=block["text"],
            page_number=raw_page["page_number"],
            bbox=block["bbox"],
            block_type=_classify_block(
                block["text"],
                block["is_table"],
                block.get("font_size"),
                body_font_size,
                block.get("is_bold", False),
            ),
            font_size=block.get("font_size"),
            is_bold=block.get("is_bold", False),
            metadata={
                "is_table": block["is_table"],
                "layout_type": block.get("layout_type", "text"),
                "layout_region": block.get("layout_region", "page"),
                "reading_order": block.get("reading_order"),
            },
        )
        for block in ordered
    )
    return PageLayout(
        page_number=raw_page["page_number"],
        width=raw_page["width"],
        height=raw_page["height"],
        blocks=layout_blocks,
    )


def _render_page_text(raw_page, repeated_signatures=None):
    return _page_layout_from_raw(raw_page, repeated_signatures).text


def extract_page_text(page, repeated_signatures=None):
    """Extract one page; document-level callers should pass repeated signatures."""
    raw_page = _extract_raw_page(page, page.number + 1)
    return _render_page_text(raw_page, repeated_signatures)


def extract_pdf_layout(pdf_path):
    with fitz.open(pdf_path) as document:
        raw_pages = [
            _extract_raw_page(document[index], index + 1)
            for index in range(len(document))
        ]
        repeated_signatures = _repeated_margin_signatures(raw_pages)
        body_font_size = _body_font_size(raw_pages)
        return [
            _page_layout_from_raw(raw_page, repeated_signatures, body_font_size)
            for raw_page in raw_pages
        ]


def extract_pdf_sections(pdf_path):
    pages = extract_pdf_layout(pdf_path)
    return build_sections(block for page in pages for block in page.blocks)


def extract_pdf_text(pdf_path):
    return [page.to_dict() for page in extract_pdf_layout(pdf_path)]
