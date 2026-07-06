"""Infrastructure adapters for ContentOS V4 intelligence."""

from contentos_intelligence.infrastructure.embedding_client import (
    GatewayEmbeddingClient,
    get_gateway_embedding_client,
    reset_embedding_client,
)

__all__ = ["GatewayEmbeddingClient", "get_gateway_embedding_client", "reset_embedding_client"]
