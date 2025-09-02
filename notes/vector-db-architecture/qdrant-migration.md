# Qdrant Collection Migration for BGE-Large

## Initial Collection Setup Migration

```python
"""
Create user preference signals collection with bge-large embeddings
Created: 2025-01-23
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import logging

logger = logging.getLogger(__name__)

MIGRATION_ID = "001_create_user_preference_signals"
DESCRIPTION = "Create user_preference_signals collection with bge-large (1024 dimensions)"

def up(client: QdrantClient):
    """Create collection with 1024-dimensional vectors (bge-large)"""
    
    # Create collection with 1024 dimensions for bge-large
    client.create_collection(
        collection_name="user_preference_signals",
        vectors_config=VectorParams(
            size=1024,  # bge-large dimensions
            distance=Distance.COSINE
        ),
        on_disk_payload=True  # Store payload on disk for large metadata
    )
    
    # Create indexes for common filters
    client.create_payload_index(
        collection_name="user_preference_signals",
        field_name="user_id",
        field_schema="integer"
    )
    
    client.create_payload_index(
        collection_name="user_preference_signals",
        field_name="signal_type",
        field_schema="keyword"
    )
    
    client.create_payload_index(
        collection_name="user_preference_signals",
        field_name="timestamp",
        field_schema="datetime"
    )
    
    logger.info(f"✅ Migration {MIGRATION_ID} completed: {DESCRIPTION}")

def down(client: QdrantClient):
    """Remove the collection"""
    
    # Delete collection
    client.delete_collection(collection_name="user_preference_signals")
    
    logger.info(f"⏪ Migration {MIGRATION_ID} rolled back - collection deleted")

def get_migration_info():
    return {
        "id": MIGRATION_ID,
        "description": DESCRIPTION,
        "created_at": "2025-01-23",
        "up": up,
        "down": down
    }
```

## Migration Design Philosophy

### Single Responsibility
This migration creates the foundational collection for suggest.watch's preference storage:
- **1024-dimensional vectors** optimized for BGE-large embeddings
- **Cosine distance** for semantic similarity matching
- **Indexed fields** for efficient user-specific queries

### Production-Ready Configuration
- **on_disk_payload=True**: Metadata stored on disk, vectors in RAM
- **Strategic indexing**: Fast filtering on user_id, signal_type, timestamp
- **Scalable design**: Handles millions of preference vectors efficiently

### Clean Architecture
- **Forward migration**: Creates the complete collection structure
- **Rollback capability**: Clean removal if needed
- **Logging**: Clear feedback on migration status
- **Metadata**: Full migration tracking information

This establishes the vector database foundation that powers suggest.watch's intelligent recommendation engine.