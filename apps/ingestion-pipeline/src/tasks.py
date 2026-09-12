import logging
from datetime import datetime

from .ingestion_service import IngestionService, VectorDBInitializationError

logger = logging.getLogger("ingestion.tasks")


class IngestionTask:
    def __init__(self, service: IngestionService):
        self.service = service
        self.running = False

    def run(self, force_update: bool = False, check_new: bool = False) -> dict:
        try:
            self.running = True
            self.service.status.running = True
            self.service.status.message = "Ingestion started"

            if not self.service.is_initialized:
                self.service.status.message = "Initializing vector database"
                if not self.service.initialize():
                    raise VectorDBInitializationError("Failed to initialize vector database")

            if force_update:
                self.service.status.message = "Full refresh"
                self.service.load_documents(force_refresh=True)
            else:
                should_check = check_new or not self.service.documents
                if should_check:
                    self.service.status.message = "Checking for new documents"
                    self.service.load_documents(check_new=True)
                else:
                    self.service.status.message = "Loading existing documents"
                    self.service.load_documents()

            new_docs_count = len(self.service.new_document_ids)

            if new_docs_count > 0 or force_update:
                self.service.status.message = f"Indexing {new_docs_count} new documents"

                if force_update:
                    docs_to_index = self.service.documents
                else:
                    docs_to_index = [doc for doc in self.service.documents if doc.id in self.service.new_document_ids]

                self.service.add_documents_to_vector_db(docs_to_index)
                self.service.status.message = f"Indexed {len(docs_to_index)} documents"
            else:
                self.service.status.message = "No new documents to index"

            self.service.status.running = False
            self.service.status.last_indexed = datetime.now().isoformat()
            self.service.status.up_to_date = True
            self.running = False

            return {
                "status": "completed",
                "new_documents": new_docs_count,
                "total_documents": len(self.service.documents),
            }

        except Exception as e:
            self.service.status.running = False
            self.service.status.message = f"Error: {str(e)}"
            self.running = False
            logger.exception("Ingestion error")
            raise
