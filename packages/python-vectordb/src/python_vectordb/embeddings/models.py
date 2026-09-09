"""Bekannte Embedding-Modelle: Aliase + Query-/Passage-Prefixe.

Alle Modelle laufen lokal über sentence-transformers. E5- und BGE-Modelle
encodieren Queries und Dokumente asymmetrisch und brauchen deshalb Prefixe,
um ihre Retrieval-Qualität zu erreichen.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingModelSpec:
    """Beschreibung eines lokalen sentence-transformers Modells."""

    model_id: str
    query_prefix: str = ""
    passage_prefix: str = ""


MODEL_SPECS: dict[str, EmbeddingModelSpec] = {
    # --- multilingual, ohne Prefixe (MiniLM/MPNet) ---
    "minilm-multilingual": EmbeddingModelSpec(
        "paraphrase-multilingual-MiniLM-L12-v2"
    ),
    "paraphrase-multilingual-MiniLM-L12-v2": EmbeddingModelSpec(
        "paraphrase-multilingual-MiniLM-L12-v2"
    ),
    "mpnet-multilingual": EmbeddingModelSpec(
        "paraphrase-multilingual-mpnet-base-v2"
    ),
    "paraphrase-multilingual-mpnet-base-v2": EmbeddingModelSpec(
        "paraphrase-multilingual-mpnet-base-v2"
    ),
    # --- E5 multilingual: query:/passage:-Prefixe erforderlich ---
    "e5-small-multilingual": EmbeddingModelSpec(
        "intfloat/multilingual-e5-small",
        query_prefix="query: ",
        passage_prefix="passage: ",
    ),
    "intfloat/multilingual-e5-small": EmbeddingModelSpec(
        "intfloat/multilingual-e5-small",
        query_prefix="query: ",
        passage_prefix="passage: ",
    ),
    "e5-base-multilingual": EmbeddingModelSpec(
        "intfloat/multilingual-e5-base",
        query_prefix="query: ",
        passage_prefix="passage: ",
    ),
    "intfloat/multilingual-e5-base": EmbeddingModelSpec(
        "intfloat/multilingual-e5-base",
        query_prefix="query: ",
        passage_prefix="passage: ",
    ),
    "e5-large-multilingual": EmbeddingModelSpec(
        "intfloat/multilingual-e5-large",
        query_prefix="query: ",
        passage_prefix="passage: ",
    ),
    "intfloat/multilingual-e5-large": EmbeddingModelSpec(
        "intfloat/multilingual-e5-large",
        query_prefix="query: ",
        passage_prefix="passage: ",
    ),
    # --- BGE-M3: Query bekommt Instruction, Dokumente bleiben unverändert ---
    "bge-m3": EmbeddingModelSpec(
        "BAAI/bge-m3",
        query_prefix="Represent this sentence for searching relevant passages: ",
    ),
    "BAAI/bge-m3": EmbeddingModelSpec(
        "BAAI/bge-m3",
        query_prefix="Represent this sentence for searching relevant passages: ",
    ),
}


def resolve_model_spec(name: str) -> EmbeddingModelSpec:
    """Löst Alias/Modellname auf; unbekannte Namen werden unverändert übernommen."""
    return MODEL_SPECS.get(name, EmbeddingModelSpec(name))
