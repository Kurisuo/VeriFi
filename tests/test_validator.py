import unittest

from data_ingestion.validator import (
    is_revision_code_section,
    normalize_text,
    validate_records,
)


def record(index, text, section_title="Useful Section", block_types=None):
    return {
        "chunk_index": index,
        "chunk_id": f"chunk-{index}",
        "text": text,
        "source_document": "sample.pdf",
        "page_number": 1,
        "page_start": 1,
        "page_end": 1,
        "page_numbers": [1],
        "section_title": section_title,
        "block_types": block_types or ["paragraph"],
        "source_fingerprint": "abc123",
        "extraction_version": "layout-v1",
        "embedding": [0.0] * 384,
    }


class ValidatorTests(unittest.TestCase):
    def test_normalize_text_dehyphenates_line_breaks(self):
        self.assertEqual(
            normalize_text("invest- \nment   policy"),
            "investment policy",
        )

    def test_revision_code_section_detection(self):
        self.assertTrue(is_revision_code_section("459374.71.0\nFA-FEES-0326\n1.828131.169"))
        self.assertFalse(is_revision_code_section("FEES AND COMPENSATION"))

    def test_validate_records_drops_duplicate_text_after_first(self):
        result = validate_records([
            record(0, "Same text."),
            record(1, "Same text."),
        ])

        self.assertEqual(result["summary"]["input_records"], 2)
        self.assertEqual(result["summary"]["validated_records"], 1)
        self.assertEqual(result["summary"]["dropped_records"], 1)
        self.assertEqual(result["dropped_records"][0]["drop_reason"], "duplicate_text")

    def test_validate_records_cleans_revision_code_heading_only(self):
        result = validate_records([
            record(
                0,
                "459374.71.0\nFA-FEES-0326\n1.828131.169",
                section_title="459374.71.0\nFA-FEES-0326\n1.828131.169",
                block_types=["heading"],
            )
        ])

        self.assertEqual(result["summary"]["validated_records"], 0)
        self.assertEqual(result["summary"]["dropped_records"], 1)
        self.assertEqual(result["dropped_records"][0]["drop_reason"], "revision_code_heading_only")

    def test_semantic_record_rejects_embedding_token_overflow(self):
        semantic = record(0, "Useful semantic content.")
        semantic.update({
            "embedding_text": "Section\n\nUseful semantic content.",
            "section_path": ["Section"],
            "semantic_unit_types": ["paragraph"],
            "chunking_version": "semantic-v1",
            "token_count": 300,
            "embedding_max_tokens": 256,
        })

        result = validate_records([semantic])

        self.assertEqual(result["summary"]["hard_errors"], 1)
        self.assertIn(
            "embedding input exceeds model token limit",
            result["records"][0]["validation_errors"],
        )


if __name__ == "__main__":
    unittest.main()
