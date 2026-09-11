"""Unit tests for the multi-target IngestionCoordinator."""

from unittest.mock import MagicMock

from src.coordinator import IngestionCoordinator, IngestionTarget


def _target(target_id: str, collection: str) -> IngestionTarget:
    service = MagicMock()
    service.is_initialized = False
    service.documents = []
    service.indexed_document_ids = set()
    service.new_document_ids = set()
    service.status = MagicMock()
    service.initialize.return_value = True
    service.check_for_updates.return_value = (False, "No new documents")
    service.get_status.return_value = {
        "service": "ingestion-pipeline",
        "status": "ok",
        "documents_count": 0,
        "indexed_documents": 0,
        "chroma_initialized": True,
        "last_indexed": None,
        "running": False,
        "message": "",
    }
    return IngestionTarget(id=target_id, collection=collection, service=service)


def test_run_all_targets_aggregates():
    coordinator = IngestionCoordinator(
        [_target("paperless", "paperless"), _target("obsidian", "obsidian")]
    )

    result = coordinator.run()
    assert result["status"] == "completed"
    assert result["errors"] == []
    assert [t["target"] for t in result["targets"]] == ["paperless", "obsidian"]


def test_run_continues_on_target_failure():
    a = _target("paperless", "paperless")
    a.service.initialize.return_value = False
    b = _target("obsidian", "obsidian")

    result = IngestionCoordinator([a, b]).run()
    assert result["status"] == "completed"
    assert len(result["errors"]) == 1
    assert result["errors"][0]["target"] == "paperless"
    # The second target still gets processed.
    assert [t["target"] for t in result["targets"]] == ["obsidian"]


def test_check_for_updates_aggregates():
    a = _target("paperless", "paperless")
    a.service.check_for_updates.return_value = (True, "Latest document: 5")
    b = _target("obsidian", "obsidian")

    needs, message = IngestionCoordinator([a, b]).check_for_updates()
    assert needs is True
    assert "paperless: Latest document: 5" in message
    assert "obsidian: No new documents" in message


def test_get_status_per_target():
    a = _target("paperless", "paperless")
    a.service.is_initialized = True
    b = _target("obsidian", "obsidian")
    b.service.is_initialized = True

    status = IngestionCoordinator([a, b]).get_status()
    assert status["status"] == "ok"
    assert len(status["targets"]) == 2
    assert status["targets"][0]["target"] == "paperless"
    assert status["targets"][1]["target"] == "obsidian"
