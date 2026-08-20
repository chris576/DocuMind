import os
import logging
import pickle
from typing import List, Optional
from datetime import datetime

from rank_bm25 import BM25Okapi
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

from python_vectordb.reranking import Reranker, RerankerFactory
from python_vectordb.vector_db import VectorDBFactory, SearchQuery, GetStatusQuery

from .models import SearchRequest, SearchResult, SearchEngineStatus

logger = logging.getLogger("retrieval")

# Download NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)

class SearchEngine:
    def __init__(self, config: dict):
        self.vector_db_type = config.get("vector_db_type", "chroma")
        self.chroma_url = config.get("chroma_url", "http://localhost:8000")
        self.qdrant_url = config.get("qdrant_url", "http://localhost:6333")
        self.qdrant_api_key = config.get("qdrant_api_key")
        self.pgvector_url = config.get("pgvector_url")
        self.collection_name = config.get("collection_name", "documents")
        self.embedding_model_name = config.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        self.embedding_provider = config.get("embedding_provider", "sentence_transformer")
        self.cross_encoder_model_name = config.get("cross_encoder_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.bm25_weight = config.get("bm25_weight", 0.3)
        self.semantic_weight = config.get("semantic_weight", 0.7)
        self.max_results = config.get("max_results", 20)
        self.bm25_file = config.get("bm25_file", "./data/bm25_index.pkl")
        
        self.vector_db = None
        self.bm25 = None
        self.tokenized_corpus = None
        self.documents = []
        self.is_initialized = False
        self.bm25_initialized = False
        
        self.reranker: Optional[Reranker] = None
        
        self.status = SearchEngineStatus()
    
    def _vector_db_config(self) -> dict:
        db_type = self.vector_db_type.lower()
        db_config = {
            "type": db_type,
            "collection": self.collection_name,
            "embedding_model": self.embedding_model_name,
            "embedding_provider": self.embedding_provider,
        }
        if db_type == "chroma":
            db_config["url"] = self.chroma_url
        elif db_type == "qdrant":
            db_config["url"] = self.qdrant_url
            db_config["api_key"] = self.qdrant_api_key
        elif db_type == "pgvector":
            db_config["url"] = self.pgvector_url
        return db_config

    def initialize(self) -> bool:
        try:
            if self.reranker is None:
                logger.info("Initializing reranker")
                self.reranker = RerankerFactory.create(
                    {"reranker_provider": "cross_encoder", "cross_encoder_model": self.cross_encoder_model_name}
                )
            
            self.is_initialized = True
            self.status.initialized = True
            self.status.last_updated = datetime.now().isoformat()
            return True
        except Exception as e:
            logger.error(f"Error initializing search engine: {str(e)}")
            self.is_initialized = False
            self.status.initialized = False
            return False
    
    def setup_vector_db(self) -> bool:
        try:
            if self.vector_db is None:
                self.vector_db = VectorDBFactory.create_reader(self._vector_db_config())

            status = self.vector_db.ask(GetStatusQuery())
            logger.info(f"Loaded vector database with {status.get('document_count', 0)} documents")
            self.status.chroma_ready = status.get("ready", False)
            self.status.documents_count = status.get("document_count", 0)
            return True
        except Exception as e:
            logger.error(f"Error setting up vector database: {str(e)}")
            self.status.chroma_ready = False
            return False
    
    def setup_bm25(self, documents: List[dict]) -> bool:
        try:
            if not documents:
                logger.error("No documents provided for BM25 setup")
                return False
            
            self.documents = documents
            self.tokenized_corpus = []
            
            stop_words = set()
            for lang in ['english', 'german', 'french', 'spanish', 'italian']:
                try:
                    stop_words.update(stopwords.words(lang))
                except:
                    pass
            
            for doc in documents:
                text = f"{doc.get('title', '')} {doc.get('correspondent', '')} {doc.get('content', '')}"
                tokens = word_tokenize(text.lower())
                filtered_tokens = [token for token in tokens if token not in stop_words]
                self.tokenized_corpus.append(filtered_tokens)
            
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            self.bm25_initialized = True
            self.status.bm25_ready = True
            self.status.bm25_documents_count = len(self.tokenized_corpus)
            
            self._save_bm25()
            logger.info(f"BM25 index built with {len(self.tokenized_corpus)} documents")
            return True
        except Exception as e:
            logger.error(f"Error setting up BM25: {str(e)}")
            self.bm25_initialized = False
            self.status.bm25_ready = False
            return False
    
    def _save_bm25(self):
        try:
            os.makedirs(os.path.dirname(self.bm25_file), exist_ok=True)
            with open(self.bm25_file, 'wb') as f:
                pickle.dump({
                    'bm25': self.bm25,
                    'tokenized_corpus': self.tokenized_corpus
                }, f)
            logger.info(f"Saved BM25 index to {self.bm25_file}")
        except Exception as e:
            logger.error(f"Error saving BM25: {str(e)}")
    
    def _load_bm25(self) -> bool:
        if not os.path.exists(self.bm25_file):
            return False
        
        try:
            with open(self.bm25_file, 'rb') as f:
                data = pickle.load(f)
            
            self.bm25 = data['bm25']
            self.tokenized_corpus = data['tokenized_corpus']
            
            if not self.bm25 or not self.tokenized_corpus:
                return False
            
            self.bm25_initialized = True
            self.status.bm25_ready = True
            self.status.bm25_documents_count = len(self.tokenized_corpus)
            logger.info(f"Loaded BM25 index with {len(self.tokenized_corpus)} documents")
            return True
        except Exception as e:
            logger.error(f"Error loading BM25: {str(e)}")
            return False
    
    def keyword_search(self, query: str, top_k: int = None) -> List[dict]:
        if not self.bm25_initialized:
            raise Exception("BM25 not initialized")
        
        top_k = top_k or self.max_results
        query_tokens = word_tokenize(query.lower())
        scores = self.bm25.get_scores(query_tokens)
        
        doc_scores = [(i, score) for i, score in enumerate(scores)]
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for i, score in doc_scores[:top_k]:
            if score > 0:
                doc = self.documents[i]
                results.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "correspondent": doc.get("correspondent", ""),
                    "date": doc.get("created", ""),
                    "score": float(score),
                    "content": doc.get("content", "")
                })
        
        return results
    
    def semantic_search(self, query: str, top_k: int = None) -> List[dict]:
        if not self.vector_db:
            raise Exception("Vector database not initialized")

        top_k = top_k or self.max_results
        results = self.vector_db.ask(SearchQuery(query=query, top_k=min(top_k, 100)))

        documents = []
        for result in results:
            metadata = result.metadata or {}
            documents.append({
                "id": result.id,
                "title": result.title,
                "correspondent": metadata.get("correspondent", ""),
                "date": metadata.get("created", ""),
                "score": float(result.score),
                "content": result.content,
            })

        return documents
    
    def hybrid_search(self, query: str, top_k: int = None) -> List[dict]:
        top_k = top_k or self.max_results
        
        keyword_results = []
        semantic_results = []
        
        try:
            keyword_results = self.keyword_search(query, top_k * 2)
        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
        
        try:
            semantic_results = self.semantic_search(query, top_k * 2)
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
        
        if not keyword_results and not semantic_results:
            raise Exception("All search methods failed")
        
        results_map = {}
        
        if keyword_results:
            max_keyword_score = max((r["score"] for r in keyword_results), default=1.0)
            for r in keyword_results:
                r["score"] = r["score"] / max_keyword_score if max_keyword_score > 0 else 0

        for result in keyword_results:
            doc_id = result["id"]
            results_map[doc_id] = {
                **result,
                "score": result["score"] * self.bm25_weight
            }
        
        for result in semantic_results:
            doc_id = result["id"]
            if doc_id in results_map:
                results_map[doc_id]["score"] += result["score"] * self.semantic_weight
            else:
                results_map[doc_id] = {
                    **result,
                    "score": result["score"] * self.semantic_weight
                }
        
        combined_results = list(results_map.values())
        combined_results.sort(key=lambda x: x["score"], reverse=True)
        
        return combined_results[:top_k]
    
    def rerank_results(self, query: str, results: List[dict], top_k: int = None) -> List[dict]:
        if not results:
            return []
        
        top_k = top_k or self.max_results
        
        try:
            if self.reranker is None:
                raise Exception("Reranker not initialized")
            return self.reranker.rerank(query, results, top_k)
        except Exception as e:
            logger.error(f"Error reranking: {str(e)}")
            for r in results:
                r["cross_score"] = 0.5
            return results[:top_k]
    
    def create_snippet(self, query: str, content: str, max_len: int = 200) -> str:
        if not content:
            return ""
        
        try:
            query_terms = set(word_tokenize(query.lower()))
            sentences = content.split(". ")
            
            sentence_scores = []
            for sentence in sentences:
                sentence_terms = set(word_tokenize(sentence.lower()))
                score = len(query_terms.intersection(sentence_terms))
                sentence_scores.append((sentence, score))
            
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            
            snippet = ""
            for sentence, _ in sentence_scores:
                if len(snippet) + len(sentence) <= max_len:
                    snippet += sentence + ". "
                else:
                    break
            
            if not snippet:
                snippet = content[:max_len] + "..."
            
            return snippet.strip()
        except Exception as e:
            logger.error(f"Error creating snippet: {str(e)}")
            return content[:max_len] + "..." if content else ""
    
    def search(self, request: SearchRequest) -> List[SearchResult]:
        if not self.is_initialized:
            self.initialize()
        
        results = self.hybrid_search(request.query, request.max_results)
        
        if request.from_date or request.to_date or request.correspondent:
            filtered = []
            for result in results:
                include = True
                
                if request.from_date and result.get("date"):
                    if result["date"].split("T")[0] < request.from_date:
                        include = False
                
                if request.to_date and result.get("date"):
                    if result["date"].split("T")[0] > request.to_date:
                        include = False
                
                if request.correspondent and result.get("correspondent"):
                    if request.correspondent.lower() not in result["correspondent"].lower():
                        include = False
                
                if include:
                    filtered.append(result)
            results = filtered
        
        reranked = self.rerank_results(request.query, results, request.max_results)
        
        formatted = []
        for result in reranked:
            snippet = self.create_snippet(request.query, result.get("content", ""))
            formatted.append(SearchResult(
                title=result.get("title", "Untitled"),
                correspondent=result.get("correspondent", ""),
                date=result.get("date", ""),
                score=result.get("score", 0),
                cross_score=result.get("cross_score", 0.5),
                snippet=snippet,
                doc_id=result.get("id"),
                content=result.get("content", "")[:500]
            ))
        
        return formatted
    
    def get_status(self) -> dict:
        return {
            "service": "retrieval-pipeline",
            "initialized": self.is_initialized,
            "vector_db_type": self.vector_db_type,
            "vector_db_ready": self.status.chroma_ready,
            "chroma_ready": self.status.chroma_ready,
            "bm25_ready": self.bm25_initialized,
            "documents_count": len(self.documents),
            "bm25_documents_count": len(self.tokenized_corpus) if self.tokenized_corpus else 0,
            "last_updated": self.status.last_updated
        }
