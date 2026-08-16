import logging
import hashlib
from typing import List, Optional, Tuple
from datetime import datetime

import requests
from sentence_transformers import SentenceTransformer

from .models import Document, IngestionStatus
from .vector_db import VectorDBFactory, ChromaVectorDB, VectorDBDocument

logger = logging.getLogger("ingestion")

class DataManager:
    def __init__(self, config: dict):
        self.paperless_url = config.get("paperless_api_url")
        self.paperless_token = config.get("paperless_api_token")
        
        if not self.paperless_url or not self.paperless_token:
            raise ValueError("Missing Paperless API configuration")
        
        self.documents: List[Document] = []
        self.indexed_document_ids: set = set()
        self.new_document_ids: set = set()
        self.is_initialized = False
        self.chroma_initialized = False
        
        self.sentence_transformer: Optional[SentenceTransformer] = None
        self.embedding_function = None
        self.chroma_client = None
        self.collection = None
        
        self.chroma_url = config.get("chroma_url", "http://localhost:8000")
        self.collection_name = config.get("collection_name", "documents")
        self.embedding_model_name = config.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        
        # Vector DB factory
        self.vector_db = VectorDBFactory.create({
            "type": config.get("vector_db_type", "chroma"),
            "url": config.get("chroma_url", "http://localhost:8000"),
            "collection": config.get("collection_name", "documents"),
            "embedding_model": config.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        })
        
        self.status = IngestionStatus()
    
    def initialize_models(self) -> bool:
        try:
            if self.sentence_transformer is None:
                logger.info("Initializing sentence transformer model")
                self.sentence_transformer = SentenceTransformer(self.embedding_model_name)
            
            if not self.vector_db.initialize():
                raise Exception("Failed to initialize vector database")
            
            self.is_initialized = True
            self.chroma_initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing models: {str(e)}")
            self.is_initialized = False
            return False
    
    def _get_headers(self):
        return {"Authorization": f"Token {self.paperless_token}"}
    
    def _compute_document_hash(self, doc: dict) -> str:
        content = f"{doc['title']}{doc['content']}{doc.get('correspondent', '')}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def check_for_updates(self) -> Tuple[bool, str]:
        logger.info("Checking for document updates")
        try:
            url = f"{self.paperless_url}/api/documents/?page=1&page_size=10"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            
            if response.status_code != 200:
                return False, f"API error: {response.status_code}"
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return False, "No documents found"
            
            newest_id = results[0].get("id")
            
            if newest_id in self.indexed_document_ids:
                return False, "No new documents detected"
            return True, "New documents detected"
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def fetch_documents_from_api(self) -> List[Document]:
        logger.info(f"Fetching documents from Paperless-ngx: {self.paperless_url}")
        
        documents = []
        page = 1
        has_next = True
        
        while has_next:
            logger.info(f"Fetching page {page}")
            url = f"{self.paperless_url}/api/documents/?page={page}&page_size=100"
            
            try:
                response = requests.get(url, headers=self._get_headers(), timeout=30)
                
                if response.status_code != 200:
                    raise Exception(f"API error: {response.status_code}")
                
                data = response.json()
                results = data.get("results", [])
                documents.extend(results)
                
                if data.get("next"):
                    page += 1
                else:
                    has_next = False
            except Exception as e:
                logger.error(f"Error fetching documents: {str(e)}")
                raise
        
        processed_docs = []
        for doc in documents:
            content = self._fetch_document_content(doc["id"])
            correspondent = self._fetch_correspondent(doc.get("correspondent"))
            tags = self._fetch_tags(doc.get("tags", []))
            
            processed_doc = Document(
                id=doc["id"],
                title=doc.get("title", ""),
                content=content,
                correspondent=correspondent,
                created=doc.get("created_date", doc.get("created", "")),
                tags=tags,
                last_updated=doc.get("modified", ""),
                hash=self._compute_document_hash({
                    "title": doc.get("title", ""),
                    "content": content,
                    "correspondent": correspondent
                })
            )
            processed_docs.append(processed_doc)
        
        return processed_docs
    
    def _fetch_document_content(self, doc_id: int) -> str:
        try:
            response = requests.get(
                f"{self.paperless_url}/api/documents/{doc_id}/download/txt/",
                headers=self._get_headers(),
                timeout=30
            )
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.warning(f"Could not fetch content for document {doc_id}: {str(e)}")
        return ""
    
    def _fetch_correspondent(self, corr_id: Optional[int]) -> str:
        if not corr_id:
            return ""
        try:
            response = requests.get(
                f"{self.paperless_url}/api/correspondents/{corr_id}/",
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("name", "")
        except Exception as e:
            logger.warning(f"Could not fetch correspondent {corr_id}: {str(e)}")
        return ""
    
    def _fetch_tags(self, tag_ids: List[int]) -> List[str]:
        tags = []
        for tag_id in tag_ids:
            try:
                response = requests.get(
                    f"{self.paperless_url}/api/tags/{tag_id}/",
                    headers=self._get_headers(),
                    timeout=10
                )
                if response.status_code == 200:
                    tags.append(response.json().get("name", ""))
            except Exception as e:
                logger.warning(f"Could not fetch tag {tag_id}: {str(e)}")
        return tags
    
    def _check_for_new_documents(self) -> List[Document]:
        logger.info("Checking for new documents")
        try:
            api_documents = self.fetch_documents_from_api()
            new_docs = []
            self.new_document_ids.clear()
            
            for doc in api_documents:
                if doc.id not in self.indexed_document_ids:
                    new_docs.append(doc)
                    self.new_document_ids.add(doc.id)
                    self.indexed_document_ids.add(doc.id)
            
            logger.info(f"Found {len(new_docs)} new documents to index")
            return new_docs
        except Exception as e:
            logger.error(f"Error checking for new documents: {str(e)}")
            return []
    
    def load_documents(self, force_refresh: bool = False, check_new: bool = False) -> List[Document]:
        if force_refresh:
            logger.info("Forcing full refresh from API")
            self.documents = self.fetch_documents_from_api()
            self.indexed_document_ids = {doc.id for doc in self.documents}
            self.new_document_ids = self.indexed_document_ids.copy()
        elif check_new:
            logger.info("Checking for new documents")
            new_docs = self._check_for_new_documents()
            if new_docs:
                self.documents.extend(new_docs)
        else:
            logger.info("Loading documents without refresh")
        
        self.status.documents_count = len(self.documents)
        self.status.last_indexed = datetime.now().isoformat()
        return self.documents
    

    
    def add_documents_to_vector_db(self, documents: List[Document]):
        if not self.is_initialized:
            if not self.initialize_models():
                raise Exception("Failed to initialize models")

        vector_documents = [
            VectorDBDocument(
                id=str(doc.id),
                title=doc.title,
                content=f"{doc.title} {doc.correspondent} {doc.content}",
                metadata={
                    "title": doc.title,
                    "correspondent": doc.correspondent,
                    "created": doc.created,
                    "tags": ", ".join(doc.tags),
                    "hash": doc.hash
                }
            )
            for doc in documents
        ]

        self.vector_db.add_documents(vector_documents)
        logger.info(f"Added/updated {len(documents)} documents to vector database")

    def get_status(self) -> dict:
        vector_status = self.vector_db.get_status() if self.vector_db else {"ready": False, "document_count": 0}

        return {
            "service": "ingestion-pipeline",
            "status": "ok" if self.is_initialized else "uninitialized",
            "documents_count": len(self.documents),
            "indexed_documents": len(self.indexed_document_ids),
            "chroma_initialized": vector_status.get("ready", False),
            "last_indexed": self.status.last_indexed,
            "running": self.status.running,
            "message": self.status.message
        }
