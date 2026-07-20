import unittest
from pathlib import Path

import fitz

from data_ingestion.chunker import chunk_pages, chunk_text
from data_ingestion.layout import Block, BlockType, PageLayout, build_sections
from data_ingestion.pdf_reader import (
    _classify_block,
    _extract_raw_page,
    _header_footer_signature,
    _is_valid_table_candidate,
    is_header_footer,
)


BROKERAGE_PDF = Path("source_files/brokerage-account-customer-agreement.pdf")


class LayoutModelTests(unittest.TestCase):
    def test_page_layout_serializes_blocks(self):
        block = Block(
            text="Account Terms",
            page_number=1,
            bbox=(10, 20, 110, 40),
            block_type=BlockType.HEADING,
        )
        page = PageLayout(page_number=1, width=612, height=792, blocks=(block,))

        self.assertEqual(page.text, "Account Terms")
        self.assertEqual(page.to_dict()["blocks"][0]["block_type"], "heading")

    def test_build_sections_starts_new_section_at_headings(self):
        blocks = (
            Block("Intro", 1, (0, 0, 10, 10)),
            Block("Fees", 1, (0, 20, 10, 30), BlockType.HEADING),
            Block("Fee detail", 1, (0, 40, 10, 50)),
        )

        sections = build_sections(blocks)

        self.assertEqual(len(sections), 2)
        self.assertIsNone(sections[0].title)
        self.assertEqual(sections[1].title, "Fees")


class StructureAwareChunkingTests(unittest.TestCase):
    def test_chunk_text_hard_splits_overlong_tokens(self):
        chunks = chunk_text("x" * 1200, max_chars=1000, overlap=100)

        self.assertEqual([len(chunk) for chunk in chunks], [1000, 200])

    def test_chunk_pages_respects_section_boundaries(self):
        pages = [
            {
                "page_number": 1,
                "text": "ignored when blocks exist",
                "blocks": [
                    {
                        "text": "Section A",
                        "page_number": 1,
                        "bbox": [0, 0, 100, 20],
                        "block_type": "heading",
                    },
                    {
                        "text": "Alpha content",
                        "page_number": 1,
                        "bbox": [0, 30, 100, 50],
                        "block_type": "paragraph",
                    },
                    {
                        "text": "Section B",
                        "page_number": 1,
                        "bbox": [0, 60, 100, 80],
                        "block_type": "heading",
                    },
                    {
                        "text": "Beta content",
                        "page_number": 1,
                        "bbox": [0, 90, 100, 110],
                        "block_type": "paragraph",
                    },
                ],
            }
        ]

        chunks = chunk_pages(pages, "sample.pdf", max_chars=1000, overlap=0)

        self.assertEqual(len(chunks), 2)
        self.assertIn("chunk_id", chunks[0])
        self.assertEqual(chunks[0]["section_title"], "Section A")
        self.assertEqual(chunks[1]["section_title"], "Section B")
        self.assertNotIn("Section B", chunks[0]["text"])
        self.assertEqual(chunks[0]["page_start"], 1)
        self.assertEqual(chunks[0]["page_end"], 1)
        self.assertEqual(chunks[0]["extraction_version"], "layout-v2")

    def test_chunk_pages_splits_large_tables_by_rows(self):
        table_text = "| Col |\n| --- |\n| " + "x" * 50 + " |\n| " + "y" * 50 + " |"
        pages = [
            {
                "page_number": 2,
                "text": table_text,
                "blocks": [
                    {
                        "text": table_text,
                        "page_number": 2,
                        "bbox": [0, 0, 200, 80],
                        "block_type": "table",
                    }
                ],
            }
        ]

        chunks = chunk_pages(pages, "sample.pdf", max_chars=20, overlap=0)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk["text"]) <= 20 for chunk in chunks))
        self.assertTrue(all(chunk["block_types"] == ["table"] for chunk in chunks))

    def test_chunk_pages_falls_back_to_plain_text_pages(self):
        chunks = chunk_pages(
            [{"page_number": 3, "text": "one two three four"}],
            "legacy.pdf",
            max_chars=7,
            overlap=0,
        )

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]["source_document"], "legacy.pdf")
        self.assertEqual(chunks[0]["page_number"], 3)
        self.assertNotIn("section_title", chunks[0])


class PdfReaderStructureTests(unittest.TestCase):
    def test_footer_signature_normalizes_page_numbers_and_symbols(self):
        self.assertEqual(
            _header_footer_signature("FIDELITY ACCOUNT® CUSTOMER AGREEMENT"),
            _header_footer_signature("2 FIDELITY ACCOUNT CUSTOMER AGREEMENT"),
        )

    def test_fidelity_footer_is_removed_in_margin(self):
        self.assertTrue(
            is_header_footer(
                "FIDELITY ACCOUNT CUSTOMER AGREEMENT 1",
                (400, 750, 570, 758),
                page_height=792,
            )
        )

    def test_font_size_can_promote_title_case_heading(self):
        block_type = _classify_block(
            "About This Agreement",
            font_size=24,
            body_font_size=10,
            is_bold=False,
        )

        self.assertEqual(block_type, BlockType.HEADING)

    @unittest.skipUnless(BROKERAGE_PDF.exists(), "sample brokerage PDF is unavailable")
    def test_rejects_decorative_box_but_keeps_real_table(self):
        with fitz.open(BROKERAGE_PDF) as document:
            decorative_box = list(document[22].find_tables().tables)[0]
            real_table = list(document[43].find_tables().tables)[0]

            self.assertFalse(
                _is_valid_table_candidate(
                    decorative_box,
                    document[22].rect.width,
                    document[22].rect.height,
                )
            )
            self.assertTrue(
                _is_valid_table_candidate(
                    real_table,
                    document[43].rect.width,
                    document[43].rect.height,
                )
            )

    @unittest.skipUnless(BROKERAGE_PDF.exists(), "sample brokerage PDF is unavailable")
    def test_three_column_margin_box_has_unique_column_major_text(self):
        with fitz.open(BROKERAGE_PDF) as document:
            page = _extract_raw_page(document[22], 23)

        text = "\n".join(block["text"] for block in page["blocks"])
        phrases = (
            "You can lose more money",
            "You are not entitled to choose",
            "Please note that any substitute payments",
        )

        self.assertFalse(any(block["is_table"] for block in page["blocks"]))
        self.assertTrue(all(text.count(phrase) == 1 for phrase in phrases))
        self.assertLess(text.index(phrases[0]), text.index(phrases[1]))
        self.assertLess(text.index(phrases[1]), text.index(phrases[2]))

    @unittest.skipUnless(BROKERAGE_PDF.exists(), "sample brokerage PDF is unavailable")
    def test_asymmetric_box_and_bottom_callout_keep_region_order(self):
        with fitz.open(BROKERAGE_PDF) as document:
            page_six = _extract_raw_page(document[5], 6)
            page_twelve = _extract_raw_page(document[11], 12)

        page_six_text = "\n".join(block["text"] for block in page_six["blocks"])
        page_twelve_text = "\n".join(block["text"] for block in page_twelve["blocks"])

        self.assertFalse(any(block["is_table"] for block in page_six["blocks"]))
        self.assertFalse(any(block["is_table"] for block in page_twelve["blocks"]))
        self.assertEqual(page_six_text.count("Things to Know"), 1)
        self.assertEqual(page_twelve_text.count("Trading in Volatile Markets"), 1)
        self.assertLess(
            page_six_text.index("Things to Know"),
            page_six_text.index("About This Agreement"),
        )
        self.assertLess(
            page_twelve_text.index("How Transactions Are Settled"),
            page_twelve_text.index("Trading in Volatile Markets"),
        )

    @unittest.skipUnless(BROKERAGE_PDF.exists(), "sample brokerage PDF is unavailable")
    def test_arbitration_box_follows_three_column_reading_order(self):
        with fitz.open(BROKERAGE_PDF) as document:
            page = _extract_raw_page(document[23], 24)

        text = "\n".join(block["text"] for block in page["blocks"])
        phrases = ("A. All parties", "G. The rules", "whom the claim is made")

        self.assertFalse(any(block["is_table"] for block in page["blocks"]))
        self.assertTrue(all(text.count(phrase) == 1 for phrase in phrases))
        self.assertLess(text.index(phrases[0]), text.index(phrases[1]))
        self.assertLess(text.index(phrases[1]), text.index(phrases[2]))


if __name__ == "__main__":
    unittest.main()
