# Interactive CLI Demo Tool

## Blog Demonstration Strategy

A simple CLI tool with user_id: 1 for everything. Perfect for blog demonstration showing the complete pipeline in action.

## CLI Demo Startup

```bash
[markholton@macair:~/git/suggest-watch → main]$ source .venv/bin/activate
(suggest-watch) [markholton@macair:~/git/suggest-watch → main]$ python cli_demo.py
🎬 suggest.watch RAG Pipeline Demo
==================================================
Connected to Qdrant: http://192.168.XX.XXX:6333
Using embedding model: bge-large (1024D)
User ID: 1

Commands:
  add <preference>     - Add a user preference
  search <query>       - Search similar preferences
  list                 - List all stored preferences
  clear               - Clear all preferences
  quit                - Exit

> 
```

## Interactive Usage Example

```bash
> add "Something like Arrival but more upbeat"
✅ Stored preference vector (1024-dim) in Qdrant

> add "Loved the philosophical themes but too slow"  
✅ Stored feedback vector (1024-dim) in Qdrant

> search "thoughtful sci-fi tonight"
🔍 Found 2 similar preferences (similarity: 0.87, 0.82)
```

## Why This Works Perfectly for Blog

### Real-Time Pipeline Demonstration
1. **User types preference** → BGE-large embedding → 1024-dim vector → Qdrant storage
2. **User searches** → Vector similarity → Retrieval results with scores  
3. **Clear pipeline flow**: Input → Processing → Storage → Retrieval

### Immediate Feedback
- **Storage confirmation**: Shows 1024-dimensional vectors being created
- **Similarity scores**: Demonstrates semantic understanding (0.87, 0.82)
- **Live interaction**: Readers can see exactly how the system responds

### Technical Transparency
- **Vector dimensions**: Makes the 1024-dim BGE-large vectors tangible
- **Similarity scoring**: Shows cosine similarity results in practice
- **Database interaction**: Real Qdrant storage and retrieval

## Blog Section Integration

This CLI demo becomes the centerpiece of **Section 3: Vector Generation Pipeline** showing:
- Live preference → vector conversion
- Actual 1024-dimensional embeddings
- Real similarity search with scores
- Complete suggest.watch intelligence in action

Perfect for demonstrating "Show the Magic" - readers see the abstract vector concepts working with real data and real results.