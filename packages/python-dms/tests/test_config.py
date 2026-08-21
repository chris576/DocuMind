"""Unit tests for python-dms config."""
from python_dms.config import DMSConfig, load_dms_config


def test_dms_config_to_dict():
    cfg = DMSConfig(
        document_provider="paperless",
        document_provider_url="http://paperless:8000",
        document_provider_token="tok123",
    )
    assert cfg.to_document_provider_config() == {
        "type": "paperless",
        "url": "http://paperless:8000",
        "token": "tok123",
    }


def test_load_dms_config_defaults(monkeypatch):
    for var in (
        "DOCUMENT_PROVIDER",
        "DOCUMENT_PROVIDER_URL",
        "DOCUMENT_PROVIDER_TOKEN",
        "PAPERLESS_API_URL",
        "PAPERLESS_API_TOKEN",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_dms_config()
    assert cfg.document_provider == "paperless"
    assert cfg.document_provider_url is None
    assert cfg.document_provider_token is None


def test_load_dms_config_prefers_new_vars(monkeypatch):
    monkeypatch.setenv("DOCUMENT_PROVIDER", "paperless")
    monkeypatch.setenv("DOCUMENT_PROVIDER_URL", "http://new:8000")
    monkeypatch.setenv("DOCUMENT_PROVIDER_TOKEN", "newtok")
    monkeypatch.setenv("PAPERLESS_API_URL", "http://old:8000")
    monkeypatch.setenv("PAPERLESS_API_TOKEN", "oldtok")

    cfg = load_dms_config()
    assert cfg.document_provider_url == "http://new:8000"
    assert cfg.document_provider_token == "newtok"


def test_load_dms_config_fallbacks_to_legacy(monkeypatch):
    monkeypatch.delenv("DOCUMENT_PROVIDER_URL", raising=False)
    monkeypatch.delenv("DOCUMENT_PROVIDER_TOKEN", raising=False)
    monkeypatch.setenv("PAPERLESS_API_URL", "http://old:8000")
    monkeypatch.setenv("PAPERLESS_API_TOKEN", "oldtok")

    cfg = load_dms_config()
    assert cfg.document_provider_url == "http://old:8000"
    assert cfg.document_provider_token == "oldtok"
