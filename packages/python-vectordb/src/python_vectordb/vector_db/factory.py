from typing import Any, Dict, List, Type

from ..embeddings import EmbeddingProviderFactory
from .base import BaseVectorDB
from .bus import VectorDBCommandBus
from .chroma import ChromaVectorDB
from .pgvector import PgVectorVectorDB
from .qdrant import QdrantVectorDB


class VectorDBFactory:
    """Creates CQRS-style command buses for the vector database.

    The concrete database is selected by the ``type`` config value (set via the
    VECTOR_DB_TYPE environment variable in the container). Supported adapters
    are registered in ``_REGISTRY``.

    - ``create_writer`` returns a write-only bus (ingestion pipeline).
    - ``create_reader`` returns a read-only bus (retrieval pipeline).
    """

    _REGISTRY: Dict[str, Type[BaseVectorDB]] = {
        "chroma": ChromaVectorDB,
        "qdrant": QdrantVectorDB,
        "pgvector": PgVectorVectorDB,
    }

    @staticmethod
    def _create_adapter(config: Dict[str, Any], embedding_provider=None) -> BaseVectorDB:
        db_type = config.get("type", "chroma").lower()

        adapter_class = VectorDBFactory._REGISTRY.get(db_type)
        if adapter_class is None:
            supported = ", ".join(sorted(VectorDBFactory._REGISTRY))
            raise ValueError(
                f"Unsupported vector database type: {db_type}. "
                f"Supported types: {supported}"
            )

        if embedding_provider is None:
            embedding_provider = EmbeddingProviderFactory.create(config)

        # Echte Dimension aus dem Provider übernehmen (768/1024 statt Default 384),
        # damit Modelle mit abweichender Dimension korrekt angelegt werden.
        adapter_config = dict(config)
        adapter_config["embedding_dimension"] = embedding_provider.dimension

        return adapter_class(adapter_config, embedding_provider)

    @staticmethod
    def create_writer(config: Dict[str, Any]) -> VectorDBCommandBus:
        """Create a write-only command bus (for the ingestion pipeline)."""
        return VectorDBCommandBus(writer=VectorDBFactory._create_adapter(config))

    @staticmethod
    def create_writers(
        config: Dict[str, Any], collections: List[str]
    ) -> Dict[str, VectorDBCommandBus]:
        """Create one write-only bus per collection, sharing a single embedding provider.

        The embedding model is loaded once and reused across all collections,
        avoiding N× memory/time when one ingestion process serves many sources.
        """
        embedding_provider = EmbeddingProviderFactory.create(config)
        writers: Dict[str, VectorDBCommandBus] = {}
        for collection in collections:
            adapter_config = dict(config)
            adapter_config["collection"] = collection
            adapter = VectorDBFactory._create_adapter(adapter_config, embedding_provider)
            writers[collection] = VectorDBCommandBus(writer=adapter)
        return writers

    @staticmethod
    def create_reader(config: Dict[str, Any]) -> VectorDBCommandBus:
        """Create a read-only command bus (for the retrieval pipeline).

        The adapter is initialized eagerly so the read-only bus can serve
        queries without exposing the write-side ``initialize()`` command.
        """
        adapter = VectorDBFactory._create_adapter(config)
        adapter.initialize()
        return VectorDBCommandBus(reader=adapter)

    @staticmethod
    def create_readers(
        config: Dict[str, Any], collections: List[str]
    ) -> Dict[str, VectorDBCommandBus]:
        """Create one read-only bus per collection, sharing a single embedding provider."""
        embedding_provider = EmbeddingProviderFactory.create(config)
        readers: Dict[str, VectorDBCommandBus] = {}
        for collection in collections:
            adapter_config = dict(config)
            adapter_config["collection"] = collection
            adapter = VectorDBFactory._create_adapter(adapter_config, embedding_provider)
            adapter.initialize()
            readers[collection] = VectorDBCommandBus(reader=adapter)
        return readers

    @staticmethod
    def create(config: Dict[str, Any]) -> VectorDBCommandBus:
        """Create a full-access command bus (backward-compatible convenience)."""
        adapter = VectorDBFactory._create_adapter(config)
        return VectorDBCommandBus(writer=adapter, reader=adapter)
