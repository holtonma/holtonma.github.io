# suggest.watch Long-term Architecture

## Core Pipeline
User conversations → Preference extraction → Vector embeddings → Similarity search → Context-enhanced LLM responses

- Future additions (reranker, fine-tuning) enhance this pipeline, don't replace it
- Foundation for all suggest.watch intelligence

## Blog Post Implementation Plan

### 1. Vector DB Setup & Migrations ✅ (Foundation Ready)
- Collection structure: user_preference_signals
- 768-dim vectors, cosine similarity, indexed fields
- Capacity/performance metrics documented

### 2. Backend Implementation 🎯 (Next Priority)
Build working code showing:

```python
# Real FastAPI endpoint
@router.post("/api/v1/chat")
async def chat_recommendation(request: ChatRequest):
    # 1. Pydantic AI extracts preferences
    # 2. Ollama generates embeddings  
    # 3. Qdrant stores vectors
    # 4. Claude generates recommendations
    return recommendations
```

### 3. Vector Generation Pipeline 🎯 (Show the Magic)
Live examples:
- User: "Something like Arrival but more upbeat"
- Preference extraction: {liked: ["Arrival"], disliked: ["depressing"]}
- Vector: [0.23, -0.45, 0.78, ...] (actual 768-dim result)
- Qdrant storage with rich metadata

### 4. RAG Integration 🎯 (The Payoff)
Demonstrate taste evolution:
- Initial query: Basic recommendations
- After 3 conversations: Context-aware suggestions using stored preferences
- Show actual vector similarity scores and LLM reasoning

## Foundation for Future Posts
This creates the foundational blog post that establishes suggest.watch as a serious AI architecture example, with all future posts building on this foundation.