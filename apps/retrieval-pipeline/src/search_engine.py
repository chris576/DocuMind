import os
import logging
import pickle
import numpy as np
from typing import List, Optional
from datetime import datetime

import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

from .models import SearchRequest, SearchResult, SearchEngineStatus

logger = logging.getLogger("retrieval")

# Download NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)

class SearchEngine:
    def __init__(self, config: dict):
        self.chroma_url = config.get("chroma_url", "http://localhost:8000")
        self.collection_name = config.get("collection_name", "documents")
        self.embedding_model_name = config.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        self.cross_encoder_model_name = config.get("cross_encoder_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.bm25_weight = config.get("bm25_weight", 0.3)
        self.semantic_weight = config.get("semantic_weight", 0.7)
        self.max_results = config.get("max_results", 20)
        self.bm25_file = config.get("bm25_file", "./data/bm25_index.pkl")
        
        self.collection = None
        self.bm25 = None
        self.tokenized_corpus = None
        self.documents = []
        self.is_initialized = False
        self.bm25_initialized = False
        
        self.sentence_transformer: Optional[SentenceTransformer] = None
        self.cross_encoder: Optional[CrossEncoder] = None
        self.embedding_function = None
        self.chroma_client = None
        
        self.status = SearchEngineStatus()
    
    def initialize(self) -> bool:
        try:
            if self.sentence_transformer is None:
                logger.info("Initializing sentence transformer")
                self.sentence_transformer = SentenceTransformer(self.embedding_model_name)
            
            if self.cross_encoder is None:
                logger.info("Initializing cross-encoder")
                self.cross_encoder = CrossEncoder(self.cross_encoder_model_name)
            
            if self.embedding_function is None:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.embedding_model_name
                )
            
            if self.chroma_client is None:
                self.chroma_client = chromadb.HttpClient(
                    host=self.chroma_url.replace("http://", "").replace("https://", "")
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
    
    def setup_chroma(self) -> bool:
        try:
            existing_collections = self.chroma_client.list_collections()
            collection_exists = any(c.name == self.collection_name for c in existing_collections)
            
            if not collection_exists:
                logger.warning(f"Collection '{self.collection_name}' does not exist")
                return False
            
            self.collection = self.chroma_client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            
            count = self.collection.count()
            logger.info(f"Loaded ChromaDB collection with {count} documents")
            self.status.chroma_ready = True
            self.status.documents_count = count
            return True
        except Exception as e:
            logger.error(f"Error setting up ChromaDB: {str(e)}")
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
        if not self.collection:
            raise Exception("ChromaDB not initialized")
        
        top_k = top_k or self.max_results
        results = self.collection.query(query_texts=[query], n_results=min(top_k, 100))
        
        if not results or "ids" not in results or not results["ids"]:
            return []
        
        documents = []
        for i, doc_id in enumerate(results["ids"][0]):
            doc = next((d for d in self.documents if str(d["id"]) == doc_id), None)
            if doc:
                distance = results["distances"][0][i] if "distances" in results else 1.0
                documents.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "correspondent": doc.get("correspondent", ""),
                    "date": doc.get("created", ""),
                    "score": float(distance),
                    "content": doc.get("content", "")
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
        
        if semantic_results:
            for r in semantic_results:
                r["score"] = 1 - r["score"] if r["score"] <= 1 else 0
        
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
            pairs = [(query, f"{r['title']} {r.get('content', '')[:500]}") for r in results]
            cross_scores = self.cross_encoder.predict(pairs)
            
            for i, score in enumerate(cross_scores):
                norm_score = 1.0 / (1.0 + np.exp(-score))
                results[i]["cross_score"] = float(norm_score)
            
            results.sort(key=lambda x: x["cross_score"], reverse=True)
            return results[:top_k]
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
            "chroma_ready": self.status.chroma_ready,
            "bm25_ready": self.bm25_initialized,
            "documents_count": len(self.documents),
            "bm25_documents_count": len(self.tokenized_corpus) if self.tokenized_corpus else 0,
            "last_updated": self.status.last_updated
        }
