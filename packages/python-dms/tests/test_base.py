"""Unit tests for the DMS base port (hash + dataclasses)."""
from python_dms.base import DocumentProvider, DocumentSummary, SourceDocument


def test_compute_hash_is_deterministic():
    doc = {"title": "T", "content": "C", "correspondent": "X"}
    assert DocumentProvider.compute_hash(doc) == DocumentProvider.compute_hash(doc)


def test_compute_hash_depends_on_fields():
    a = DocumentProvider.compute_hash(
        {"title": "A", "content": "C", "correspondent": "X"}
    )
    b = DocumentProvider.compute_hash(
        {"title": "B", "content": "C", "correspondent": "X"}
    )
    assert a != b


def test_compute_hash_missing_fields_use_empty():
    # Missing keys must not crash.
    DocumentProvider.compute_hash({})


def test_source_document_defaults():
    doc = SourceDocument(id="1", title="T", content="C")
    assert doc.correspondent == ""
    assert doc.document_type == ""
    assert doc.storage_path == ""
    assert doc.created == ""
    assert doc.tags == []
    assert doc.last_updated == ""
    assert doc.hash == ""
    assert doc.metadata == {}


def test_document_summary_defaults():
    summary = DocumentSummary(id="1")
    assert summary.checksum == ""
    assert summary.modified == ""
