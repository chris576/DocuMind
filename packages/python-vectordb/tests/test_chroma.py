"""Unit tests for ChromaDB metadata flattening."""
from python_vectordb.vector_db.chroma import ChromaVectorDB


def test_flatten_metadata_serializes_nested_values():
    metadata = {
        "scalar_str": "text",
        "scalar_int": 42,
        "scalar_float": 1.5,
        "list": [1, 2, 3],
        "dict": {"amount": "EUR11.10"},
        "none": None,
    }
    flat = ChromaVectorDB._flatten_metadata(metadata)

    assert flat["scalar_str"] == "text"
    assert flat["scalar_int"] == 42
    assert flat["scalar_float"] == 1.5
    assert flat["list"] == "[1, 2, 3]"
    assert flat["dict"] == '{"amount": "EUR11.10"}'
    assert flat["none"] is None


def test_flatten_metadata_empty():
    assert ChromaVectorDB._flatten_metadata({}) == {}
