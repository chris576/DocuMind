"""Unit tests for the VectorDB factory and adapter setup."""
from unittest.mock import MagicMock, patch

import pytest

from python_vectordb.vector_db.bus import VectorDBCommandBus
from python_vectordb.vector_db.factory import VectorDBFactory


@patch("python_vectordb.vector_db.factory.EmbeddingProviderFactory.create")
def test_create_adapter_unknown_type(mock_embed):
    with pytest.raises(ValueError, match="Unsupported vector database type"):
        VectorDBFactory._create_adapter({"type": "nope"})


@patch("python_vectordb.vector_db.factory.EmbeddingProviderFactory.create")
def test_create_writer_returns_bus(mock_embed):
    mock_embed.return_value = MagicMock()
    bus = VectorDBFactory.create_writer({"type": "chroma"})
    assert isinstance(bus, VectorDBCommandBus)


@patch("python_vectordb.vector_db.factory.EmbeddingProviderFactory.create")
def test_create_reader_initializes(mock_embed):
    with patch(
        "python_vectordb.vector_db.factory.VectorDBFactory._create_adapter"
    ) as mock_create:
        mock_adapter = MagicMock()
        mock_adapter.initialize.return_value = True
        mock_create.return_value = mock_adapter

        bus = VectorDBFactory.create_reader({"type": "chroma"})
        assert isinstance(bus, VectorDBCommandBus)
        mock_adapter.initialize.assert_called_once()


@patch("python_vectordb.vector_db.factory.EmbeddingProviderFactory.create")
def test_create_full_access(mock_embed):
    with patch(
        "python_vectordb.vector_db.factory.VectorDBFactory._create_adapter"
    ) as mock_create:
        mock_create.return_value = MagicMock()
        bus = VectorDBFactory.create({"type": "chroma"})
        assert isinstance(bus, VectorDBCommandBus)
        # Full access bus has both writer and reader.
        assert bus._writer is not None
        assert bus._reader is not None


def test_factory_registry_contains_all():
    assert set(VectorDBFactory._REGISTRY) == {"chroma", "qdrant", "pgvector"}


@patch("python_vectordb.vector_db.factory.EmbeddingProviderFactory.create")
def test_create_writers_shares_embedding(mock_embed):
    mock_embed.return_value = MagicMock(dimension=384)
    writers = VectorDBFactory.create_writers({"type": "chroma"}, ["c1", "c2"])
    assert set(writers) == {"c1", "c2"}
    # The embedding model is loaded exactly once, not once per collection.
    assert mock_embed.call_count == 1
    for bus in writers.values():
        assert isinstance(bus, VectorDBCommandBus)


@patch("python_vectordb.vector_db.factory.EmbeddingProviderFactory.create")
def test_create_readers_shares_embedding(mock_embed):
    with patch(
        "python_vectordb.vector_db.factory.VectorDBFactory._create_adapter"
    ) as mock_create:
        mock_adapter = MagicMock()
        mock_adapter.initialize.return_value = True
        mock_create.return_value = mock_adapter

        readers = VectorDBFactory.create_readers({"type": "chroma"}, ["c1", "c2"])
        assert set(readers) == {"c1", "c2"}
        # One embedding provider, shared across the per-collection readers.
        assert mock_embed.call_count == 1
        # One adapter per collection, each initialized eagerly.
        assert mock_create.call_count == 2
        assert mock_adapter.initialize.call_count == 2
        for bus in readers.values():
            assert isinstance(bus, VectorDBCommandBus)
