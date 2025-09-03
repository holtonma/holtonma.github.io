# LLM Setup for Part 2

## Ollama Model Inventory

```bash
root@ollama-ai1:~# ollama list
NAME                ID              SIZE      MODIFIED      
bge-large:latest    b3d71c928059    670 MB    2 minutes ago    
llama3.1:8b         46e0c10c039e    4.9 GB    42 hours ago 
```

## Complete Local AI Stack Ready

**Models available**:
- **bge-large:latest**: 670 MB embedding model (for vector generation)
- **llama3.1:8b**: 4.9 GB language model (for recommendation generation)
- **Total footprint**: ~5.5 GB for complete RAG pipeline

## Architecture Benefits

- **Same container**: Both embedding and generation models on ollama-ai1
- **No external API calls**: Complete RAG pipeline runs locally
- **Privacy maintained**: All user preferences and recommendations stay local
- **Consistent performance**: No network latency or rate limiting

## Pipeline Flow

1. **User query** → BGE-large (embeddings) → Qdrant (similarity search)
2. **Similar preferences** → Llama 3.1 8B (recommendation generation)
3. **Movie recommendations** → User

The foundation from Part 1 (vector database + semantic search) now has the generation capability to complete the RAG loop.