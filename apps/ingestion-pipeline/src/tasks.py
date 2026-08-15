import logging
from typing import Optional
from datetime import datetime

from .data_manager import DataManager

logger = logging.getLogger("ingestion.tasks")

class IngestionTask:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.running = False
    
    def run(self, force_update: bool = False, check_new: bool = False) -> dict:
        try:
            self.running = True
            self.data_manager.status.running = True
            self.data_manager.status.message = "Ingestion started"
            
            if not self.data_manager.is_initialized:
                self.data_manager.status.message = "Initializing models"
                if not self.data_manager.initialize_models():
                    raise Exception("Failed to initialize models")
            
            if force_update:
                self.data_manager.status.message = "Full refresh"
                self.data_manager.load_documents(force_refresh=True)
            else:
                should_check = check_new or not self.data_manager.documents
                if should_check:
                    self.data_manager.status.message = "Checking for new documents"
                    self.data_manager.load_documents(check_new=True)
                else:
                    self.data_manager.status.message = "Loading existing documents"
                    self.data_manager.load_documents()
            
            new_docs_count = len(self.data_manager.new_document_ids)
            
            if new_docs_count > 0 or force_update:
                self.data_manager.status.message = f"Indexing {new_docs_count} new documents"
                
                if force_update:
                    docs_to_index = self.data_manager.documents
                else:
                    docs_to_index = [
                        doc for doc in self.data_manager.documents
                        if doc.id in self.data_manager.new_document_ids
                    ]
                
                self.data_manager.add_documents_to_vector_db(docs_to_index)
                self.data_manager.status.message = f"Indexed {len(docs_to_index)} documents"
            else:
                self.data_manager.status.message = "No new documents to index"
            
            self.data_manager.status.running = False
            self.data_manager.status.last_indexed = datetime.now().isoformat()
            self.data_manager.status.up_to_date = True
            self.running = False
            
            return {
                "status": "completed",
                "new_documents": new_docs_count,
                "total_documents": len(self.data_manager.documents)
            }
            
        except Exception as e:
            self.data_manager.status.running = False
            self.data_manager.status.message = f"Error: {str(e)}"
            self.running = False
            logger.error(f"Ingestion error: {str(e)}")
            raise
