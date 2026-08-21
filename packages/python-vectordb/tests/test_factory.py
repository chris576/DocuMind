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
