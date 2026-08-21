"""Unit tests for the DocumentProviderFactory."""
import pytest

from python_dms.docspell import DocspellDocumentProvider
from python_dms.factory import DocumentProviderFactory
from python_dms.paperless import PaperlessDocumentProvider


def test_create_paperless():
    provider = DocumentProviderFactory.create(
        {"type": "paperless", "url": "http://p", "token": "t"}
    )
    assert isinstance(provider, PaperlessDocumentProvider)


def test_create_docspell():
    provider = DocumentProviderFactory.create(
        {"type": "docspell", "url": "http://d", "token": "t"}
    )
    assert isinstance(provider, DocspellDocumentProvider)


def test_create_defaults_to_paperless():
    provider = DocumentProviderFactory.create({"url": "http://p", "token": "t"})
    assert isinstance(provider, PaperlessDocumentProvider)


def test_create_unknown_provider():
    with pytest.raises(ValueError, match="Unknown document provider"):
        DocumentProviderFactory.create({"type": "nope", "url": "http://p", "token": "t"})
