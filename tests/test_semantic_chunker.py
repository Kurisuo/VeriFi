import unittest

from data_ingestion.semantic_chunker import (
    _looks_tabular_text,
    normalize_semantic_text,
    semantic_chunk_pages,
    split_sentences,
)


def page_with_blocks(blocks):
    return [{
        "page_number": 1,
        "text": "",
        "blocks": blocks,
    }]


def block(text, block_type="paragraph", font_size=10, is_bold=False, y=0):
    return {
        "text": text,
        "page_number": 1,
        "bbox": [0, y, 400, y + 20],
        "block_type": block_type,
        "font_size": font_size,
        "is_bold": is_bold,
        "metadata": {"reading_order": y},
    }


class SemanticChunkerTests(unittest.TestCase):
    def test_attaches_heading_to_content_and_section_path(self):
        records = semantic_chunk_pages(
            page_with_blocks([
                block("Account Features", "heading", font_size=18, is_bold=True),
                block("Feature details belong with the heading.", y=30),
            ]),
            "sample.pdf",
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["section_path"], ["Account Features"])
        self.assertIn("Account Features", records[0]["text"])
        self.assertIn("Feature details", records[0]["text"])
        self.assertNotEqual(records[0]["block_types"], ["heading"])

    def test_style_only_bold_fragment_is_rejoined(self):
        records = semantic_chunk_pages(
            page_with_blocks([
                block(
                    "If you cannot meet a margin call, Fidelity can force the sale of assets in your",
                    "heading",
                    font_size=10,
                    is_bold=True,
                ),
                block("account without prior notice.", y=30),
            ]),
            "sample.pdf",
        )

        self.assertEqual(len(records), 1)
        self.assertIn("your account without prior notice.", records[0]["text"])
        self.assertEqual(records[0]["section_path"], [])

    def test_bold_bullet_is_not_promoted_to_section_heading(self):
        records = semantic_chunk_pages(
            page_with_blocks([
                block(
                    "• Unless you select yes, you are not subject to backup withholding because:",
                    "heading",
                    font_size=10,
                    is_bold=True,
                ),
                block("• You are exempt from backup withholding.", "list", y=30),
            ]),
            "sample.pdf",
        )

        self.assertEqual(records[0]["section_path"], [])
        self.assertIn("backup withholding", records[0]["text"])

    def test_sentence_safe_splitting_respects_maximum(self):
        text = "First sentence has context. Second sentence adds details. Third sentence concludes."
        records = semantic_chunk_pages(
            page_with_blocks([block(text)]),
            "sample.pdf",
            target_chars=45,
            max_chars=60,
            overlap_chars=25,
        )

        self.assertGreater(len(records), 1)
        self.assertTrue(all(len(record["text"]) <= 60 for record in records))
        self.assertTrue(all(record["text"].rstrip().endswith(".") for record in records))

    def test_table_chunks_repeat_header_rows(self):
        table = "\n".join([
            "| Name | Fee |",
            "| --- | --- |",
            "| Alpha | $10 |",
            "| Beta | $20 |",
            "| Gamma | $30 |",
        ])
        records = semantic_chunk_pages(
            page_with_blocks([block(table, "table")]),
            "sample.pdf",
            target_chars=45,
            max_chars=60,
            overlap_chars=0,
        )

        self.assertGreater(len(records), 1)
        self.assertTrue(all("| Name | Fee |" in record["text"] for record in records))

    def test_dehyphenates_only_real_line_breaks(self):
        self.assertEqual(normalize_semantic_text("invest-\nment"), "investment")
        self.assertEqual(normalize_semantic_text("risk-adjusted"), "risk-adjusted")

    def test_sentence_split_keeps_abbreviation_inside_sentence(self):
        sentences = split_sentences("The U.S. market opened. Trading continued.")
        self.assertEqual(sentences, ["The U.S. market opened.", "Trading continued."])

    def test_detects_dense_financial_rows_as_table_content(self):
        text = "\n".join([
            "% Charged on Buy",
            "$0-$9,999",
            "2.90%",
            "$10,000-$49,999",
            "2.50%",
            "$50,000-$99,999",
            "1.98%",
            "$100,000+",
        ])
        self.assertTrue(_looks_tabular_text(text))


if __name__ == "__main__":
    unittest.main()
