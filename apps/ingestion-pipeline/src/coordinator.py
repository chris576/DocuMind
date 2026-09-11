"""Coordinator that runs ingestion across multiple document sources (targets).

Each target wraps its own DocumentProvider + write-only vector-db bus (one
collection per target). The coordinator runs all targets best-effort: a failing
target is recorded and the remaining targets continue.
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple

from .ingestion_service import IngestionService
from .tasks import IngestionTask

logger = logging.getLogger("ingestion.coordinator")


@dataclass
class IngestionTarget:
    id: str
    collection: str
    service: IngestionService


class IngestionCoordinator:
    def __init__(self, targets: List[IngestionTarget]):
        self.targets = targets
        self.running = False

    def run(self, force_update: bool = False, check_new: bool = False) -> dict:
        self.running = True
        results: List[dict] = []
        errors: List[dict] = []
        total_new = 0
        total_documents = 0

        try:
            for target in self.targets:
                try:
                    task = IngestionTask(target.service)
                    result = task.run(force_update=force_update, check_new=check_new)
                    results.append(
                        {
                            "target": target.id,
                            "collection": target.collection,
                            **result,
                        }
                    )
                    total_new += int(result.get("new_documents", 0))
                    total_documents += int(result.get("total_documents", 0))
                except Exception as e:  # noqa: BLE001 — best-effort per target
                    logger.error(f"Ingestion target '{target.id}' failed: {e}")
                    errors.append(
                        {
                            "target": target.id,
                            "collection": target.collection,
                            "error": str(e),
                        }
                    )

            return {
                "status": "completed",
                "new_documents": total_new,
                "total_documents": total_documents,
                "targets": results,
                "errors": errors,
            }
        finally:
            self.running = False

    def check_for_updates(self) -> Tuple[bool, str]:
        messages = []
        needs_update = False
        for target in self.targets:
            ok, message = target.service.check_for_updates()
            needs_update = needs_update or ok
            messages.append(f"{target.id}: {message}")
        return needs_update, " | ".join(messages)

    def get_status(self) -> dict:
        targets_status = [
            {
                "target": target.id,
                "collection": target.collection,
                **target.service.get_status(),
            }
            for target in self.targets
        ]
        all_initialized = bool(self.targets) and all(
            target.service.is_initialized for target in self.targets
        )
        return {
            "service": "ingestion-pipeline",
            "status": "ok" if all_initialized else "uninitialized",
            "documents_count": sum(len(target.service.documents) for target in self.targets),
            "indexed_documents": sum(
                len(target.service.indexed_document_ids) for target in self.targets
            ),
            "targets": targets_status,
            "running": self.running,
            "message": "",
        }
