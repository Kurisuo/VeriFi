from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


BoundingBox = tuple[float, float, float, float]


class BlockType(StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST = "list"
    TABLE = "table"
    HEADER_FOOTER = "header_footer"


@dataclass(frozen=True, slots=True)
class Block:
    text: str
    page_number: int
    bbox: BoundingBox
    block_type: BlockType = BlockType.PARAGRAPH
    font_size: float | None = None
    is_bold: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.page_number < 1:
            raise ValueError("page_number must be one-based")
        if len(self.bbox) != 4:
            raise ValueError("bbox must contain four coordinates")

        x0, y0, x1, y1 = self.bbox
        if x1 < x0 or y1 < y0:
            raise ValueError("bbox must be ordered as (x0, y0, x1, y1)")

        object.__setattr__(self, "text", self.text.strip())
        object.__setattr__(
            self,
            "bbox",
            tuple(float(value) for value in self.bbox),
        )
        if not isinstance(self.block_type, BlockType):
            object.__setattr__(self, "block_type", BlockType(self.block_type))

    @property
    def is_structural(self):
        return self.block_type in {BlockType.HEADING, BlockType.TABLE}

    def to_dict(self):
        return {
            "text": self.text,
            "page_number": self.page_number,
            "bbox": list(self.bbox),
            "block_type": self.block_type.value,
            "font_size": self.font_size,
            "is_bold": self.is_bold,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class Section:
    title: str | None
    blocks: tuple[Block, ...]
    level: int = 1

    def __post_init__(self):
        object.__setattr__(self, "blocks", tuple(self.blocks))
        if self.level < 1:
            raise ValueError("level must be positive")

    @property
    def text(self):
        return "\n\n".join(block.text for block in self.blocks if block.text).strip()

    @property
    def page_numbers(self):
        return tuple(
            sorted({block.page_number for block in self.blocks if block.page_number})
        )

    def to_dict(self):
        return {
            "title": self.title,
            "level": self.level,
            "page_numbers": list(self.page_numbers),
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(frozen=True, slots=True)
class PageLayout:
    page_number: int
    width: float
    height: float
    blocks: tuple[Block, ...]

    def __post_init__(self):
        object.__setattr__(self, "blocks", tuple(self.blocks))

    @property
    def text(self):
        return "\n\n".join(block.text for block in self.blocks if block.text).strip()

    def to_dict(self):
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "text": self.text,
            "blocks": [block.to_dict() for block in self.blocks],
        }


def build_sections(blocks):
    sections = []
    current_title = None
    current_blocks = []

    for block in blocks:
        if block.block_type == BlockType.HEADING:
            if current_blocks:
                sections.append(Section(current_title, tuple(current_blocks)))
            current_title = block.text
            current_blocks = [block]
        else:
            current_blocks.append(block)

    if current_blocks:
        sections.append(Section(current_title, tuple(current_blocks)))

    return sections


def flatten_page_blocks(pages):
    blocks = []
    for page in pages:
        if isinstance(page, PageLayout):
            blocks.extend(page.blocks)
        else:
            blocks.extend(page.get("layout_blocks", page.get("blocks", [])))
    return blocks
