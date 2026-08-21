"""Unit tests for the Docspell placeholder provider."""
import pytest

from python_dms.docspell import DocspellDocumentProvider


def test_requires_url_and_token():
    with pytest.raises(ValueError, match="Missing document provider configuration"):
        DocspellDocumentProvider({})
    with pytest.raises(ValueError, match="Missing document provider configuration"):
        DocspellDocumentProvider({"url": "http://d"})


def test_uses_fallback_keys():
    provider = DocspellDocumentProvider(
        {"document_provider_url": "http://d", "document_provider_token": "t"}
    )
    assert provider.base_url == "http://d"
    assert provider.token == "t"


def test_not_implemented_methods():
    provider = DocspellDocumentProvider({"url": "http://d", "token": "t"})
    with pytest.raises(NotImplementedError):
        provider.check_for_updates()
    with pytest.raises(NotImplementedError):
        provider.fetch_documents()
    with pytest.raises(NotImplementedError):
        provider.fetch_document_content("1")
    with pytest.raises(NotImplementedError):
        provider.fetch_document_summaries()
