# BGE-Large Embedding API Test

## Direct API Testing

Testing the BGE-large embedding model via Ollama API to verify vector generation:

```bash
$ curl -X POST http://192.168.XX.XXX:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "bge-large", "prompt": "test"}' \
  --max-time 10

{"embedding":[0.10005388408899307,0.04916883632540703,-0.023901909589767456,0.3443702161312103,-0.3103911578655243,0.2628104090690613,…32476807,0.15598803758621216]}
```

## API Response Analysis

### Vector Properties
- **Model**: bge-large successfully responding
- **Dimensions**: 1024 floating-point values (truncated for display)
- **Sample values**: Mix of positive/negative floats representing semantic features
- **Response time**: Sub-10 second completion (actual response was faster)

### Technical Verification
- **API endpoint**: Ollama embedding service operational on AI X1 Pro
- **Model availability**: BGE-large loaded and ready for inference
- **Data format**: JSON response with complete 1024-dimensional vector
- **Network access**: Direct container communication working

## Pipeline Integration

This API test confirms the embedding generation step in suggest.watch:
1. **User preference text** → Ollama API call
2. **BGE-large processing** → 1024-dimensional semantic vector
3. **JSON response** → Vector ready for Qdrant storage
4. **Complete pipeline** → Text-to-vector conversion operational

## CLI Pipeline in Action

Full pipeline demonstration showing the complete preference processing workflow:

```bash
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

> add Something like Arrival but more upbeat 
📝 Processing: 'Something like Arrival but more upbeat'
🧠 Extracting preference signals with Pydantic AI...
   ✅ Extracted preferences with Pydantic AI
🔢 Generating 1024-dimensional embedding with bge-large...
   📡 Connecting to Ollama at 192.168.XX.XXX:11434
   ✅ Received embedding: 1024 dimensions
💾 Storing in Qdrant with metadata...
✅ Stored preference vector in Qdrant
   📊 Vector dimensions: 1024
   🏷️  Preference strength: 0.80
   📝 Extracted metadata: ['reference_content', 'genre', 'themes', 'mood', 'desired_tone', 'complexity_level', 'pacing_preference', 'format'] 
```

## Complete Pipeline Breakdown

### Step 1: Preference Extraction (Pydantic AI)
- **Input**: "Something like Arrival but more upbeat"
- **Processing**: Pydantic AI extracts structured preferences
- **Output**: Rich metadata including genre, mood, desired_tone, etc.

### Step 2: Vector Generation (BGE-large)
- **API call**: Ollama endpoint (192.168.XX.XXX:11434)
- **Model**: BGE-large processes the structured preference
- **Result**: 1024-dimensional semantic embedding

### Step 3: Vector Storage (Qdrant)
- **Database**: Stores vector with complete metadata payload
- **Dimensions**: Confirms 1024-dim vector storage
- **Intelligence**: Preference strength score (0.80) calculated
- **Metadata**: 8 structured preference attributes preserved

## Additional Preference Examples

Building a rich preference profile with varied input types:

```bash
> add I like sci-fi, but with good characters, it can't be just about the nerdy sets
📝 Processing: 'I like sci-fi, but with good characters, it can't be just about the nerdy sets'
🧠 Extracting preference signals with Pydantic AI...
   ✅ Extracted preferences with Pydantic AI
🔢 Generating 1024-dimensional embedding with bge-large...
   📡 Connecting to Ollama at 192.168.XX.XXX:11434
   ✅ Received embedding: 1024 dimensions
💾 Storing in Qdrant with metadata...
✅ Stored preference vector in Qdrant
   📊 Vector dimensions: 1024
   🏷️  Preference strength: 0.70
   📝 Extracted metadata: ['subgenre', 'importance']

> add I need character development, not just explosions and CGI
📝 Processing: 'I need character development, not just explosions and CGI'
🧠 Extracting preference signals with Pydantic AI...
   ✅ Extracted preferences with Pydantic AI
🔢 Generating 1024-dimensional embedding with bge-large...
   📡 Connecting to Ollama at 192.168.XX.XXX:11434
   ✅ Received embedding: 1024 dimensions
💾 Storing in Qdrant with metadata...
✅ Stored preference vector in Qdrant
   📊 Vector dimensions: 1024
   🏷️  Preference strength: 0.80
   📝 Extracted metadata: ['themes', 'anti_preferences', 'complexity_preference', 'pacing_preference', 'emotional_weight', 'narrative_style']

> add More like The Martian less like depressing Black Mirror
📝 Processing: 'More like The Martian less like depressing Black Mirror'
🧠 Extracting preference signals with Pydantic AI...
   ✅ Extracted preferences with Pydantic AI
🔢 Generating 1024-dimensional embedding with bge-large...
   📡 Connecting to Ollama at 192.168.XX.XXX:11434
   ✅ Received embedding: 1024 dimensions
💾 Storing in Qdrant with metadata...
✅ Stored preference vector in Qdrant
   📊 Vector dimensions: 1024
   🏷️  Preference strength: 0.80
   📝 Extracted metadata: ['genre_preferences', 'mood_preferences', 'theme_preferences', 'pacing_preferences', 'complexity_preferences', 'reference_titles']

> add No superhero movies, I'm burned out on them
📝 Processing: 'No superhero movies, I'm burned out on them'
🧠 Extracting preference signals with Pydantic AI...
   ✅ Extracted preferences with Pydantic AI
🔢 Generating 1024-dimensional embedding with bge-large...
   📡 Connecting to Ollama at 192.168.XX.XXX:11434
   ✅ Received embedding: 1024 dimensions
💾 Storing in Qdrant with metadata...
✅ Stored preference vector in Qdrant
   📊 Vector dimensions: 1024
   🏷️  Preference strength: -0.80
   📝 Extracted metadata: ['reason', 'strength', 'genre', 'subgenres', 'temporal_state']
```

## Intelligence Patterns Emerging

### Preference Strength Variations
- **Character-focused sci-fi**: 0.70 (moderate positive)
- **Character development need**: 0.80 (strong positive)  
- **The Martian vs Black Mirror**: 0.80 (strong comparative preference)
- **No superhero movies**: -0.80 (strong negative - note the negative score!)

### Metadata Sophistication
- **Simple preferences**: 2 metadata fields (subgenre, importance)
- **Complex needs**: 6 metadata fields (themes, anti_preferences, etc.)
- **Comparative statements**: 6 fields including reference_titles
- **Negative preferences**: 5 fields including temporal_state (burnout)

### Semantic Understanding
The pipeline successfully identifies:
- **Positive preferences**: Character development, The Martian style
- **Negative preferences**: Explosions, CGI-heavy, Black Mirror tone, superhero burnout
- **Comparative reasoning**: "More like X, less like Y" patterns
- **Temporal context**: "Burned out" suggests current state, not permanent dislike

This demonstrates the complete suggest.watch intelligence pipeline - from natural language input to structured, searchable preference vectors with rich semantic understanding.