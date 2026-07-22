"""API bridge tests: retrieval mapper wire format."""

from retrieval import mapper


def test_api_mapper_single_result():
    raw = [
        {
            "score": 0.94,
            "text": "Margin calls must be satisfied within three days.",
            "source_document": "terms-and-conditions.pdf",
            "page_number": 12,
        }
    ]

    sources = mapper.to_sources(raw)

    assert sources == [
        {
            "doc": "terms-and-conditions.pdf",
            "page": 12,
            "snippet": "Margin calls must be satisfied within three days.",
            "score": 0.94,
        }
    ]


def test_api_mapper_preserves_order_and_types():
    raw = [
        {
            "score": "0.5",
            "text": "first",
            "source_document": "a.pdf",
            "page_number": 1,
        },
        {
            "score": 0.9,
            "text": "second",
            "source_document": "b.pdf",
            "page_number": 2,
        },
    ]

    sources = mapper.to_sources(raw)

    assert len(sources) == 2
    assert sources[0]["doc"] == "a.pdf"
    assert sources[1]["page"] == 2
    assert isinstance(sources[0]["page"], int)
    assert isinstance(sources[0]["score"], float)
