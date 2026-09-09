"""Bekannte Cross-Encoder-Modelle: Aliase auf volle HF-Modell-IDs.

Alle Modelle laufen lokal über sentence-transformers (CrossEncoder). Anders
als Embedding-Modelle brauchen Cross-Encoder keine Query-/Passage-Prefixe.
"""

RERANKER_MODEL_SPECS: dict[str, str] = {
    # --- MS MARCO (englisch-zentriert, logit-Ausgabe) ---
    "msmarco-minilm": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "cross-encoder/ms-marco-MiniLM-L-6-v2": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "msmarco-minilm-small": "cross-encoder/ms-marco-MiniLM-L-4-v2",
    "cross-encoder/ms-marco-MiniLM-L-4-v2": "cross-encoder/ms-marco-MiniLM-L-4-v2",
    # --- multilingual / deutsch-tauglich ---
    "mmarco-multilingual": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    "bge-reranker-base": "BAAI/bge-reranker-base",
    "BAAI/bge-reranker-base": "BAAI/bge-reranker-base",
    "bge-reranker-m3": "BAAI/bge-reranker-v2-m3",
    "BAAI/bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3",
    "mxbai-rerank-base": "mixedbread-ai/mxbai-rerank-base-v1",
    "mixedbread-ai/mxbai-rerank-base-v1": "mixedbread-ai/mxbai-rerank-base-v1",
    "jina-reranker-multilingual": "jinaai/jina-reranker-v2-base-multilingual",
    "jinaai/jina-reranker-v2-base-multilingual": "jinaai/jina-reranker-v2-base-multilingual",
}


def resolve_reranker_model(name: str) -> str:
    """Löst Alias/Modellname auf; unbekannte Namen werden unverändert übernommen."""
    return RERANKER_MODEL_SPECS.get(name, name)
