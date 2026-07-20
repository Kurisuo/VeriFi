import json
import tempfile
import unittest
from pathlib import Path

from data_ingestion.extraction_cache import (
    cache_path_for,
    load_or_extract_pdf_layout,
)


class ExtractionCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temporary_directory.name) / "cache"
        self.pdf_path = Path(self.temporary_directory.name) / "sample.pdf"
        self.pdf_path.write_bytes(b"sample PDF bytes")
        self.fingerprint = "abc123"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_cold_then_warm_cache_avoids_second_extraction(self):
        calls = []

        def extractor(path):
            calls.append(path)
            return [{"page_number": 1, "text": "Hello", "blocks": []}]

        cold_pages, cold_event = load_or_extract_pdf_layout(
            self.pdf_path, self.fingerprint, self.cache_dir, extractor
        )
        warm_pages, warm_event = load_or_extract_pdf_layout(
            self.pdf_path, self.fingerprint, self.cache_dir, extractor
        )

        self.assertEqual(cold_pages, warm_pages)
        self.assertEqual(len(calls), 1)
        self.assertEqual(cold_event["status"], "miss")
        self.assertEqual(warm_event["status"], "hit")

    def test_different_fingerprint_has_a_different_cache_entry(self):
        calls = []

        def extractor(path):
            calls.append(path)
            return []

        load_or_extract_pdf_layout(
            self.pdf_path, self.fingerprint, self.cache_dir, extractor
        )
        load_or_extract_pdf_layout(
            self.pdf_path, "changed", self.cache_dir, extractor
        )

        self.assertEqual(len(calls), 2)
        self.assertNotEqual(
            cache_path_for(self.fingerprint, self.cache_dir),
            cache_path_for("changed", self.cache_dir),
        )

    def test_corrupt_cache_is_replaced(self):
        cache_path = cache_path_for(self.fingerprint, self.cache_dir)
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text("not json", encoding="utf-8")

        pages, event = load_or_extract_pdf_layout(
            self.pdf_path,
            self.fingerprint,
            self.cache_dir,
            lambda path: [{"page_number": 1, "text": "Recovered"}],
        )

        self.assertEqual(event["status"], "invalid")
        self.assertEqual(pages[0]["text"], "Recovered")
        with cache_path.open("r", encoding="utf-8") as file:
            self.assertEqual(json.load(file)["pages"], pages)


if __name__ == "__main__":
    unittest.main()
