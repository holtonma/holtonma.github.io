# LLM Text Generation Service Architecture

## Overview

The LLMService completes the RAG loop by generating actual movie recommendations based on vector search context. It's designed to be model-agnostic while currently using Ollama Llama 3.1 8B for local inference.

## Service Responsibilities

1. **Movie Recommendation Generation** - Convert vector search results into specific movie titles
2. **Contextual Reasoning** - Use retrieved user preferences to explain recommendations
3. **Structured Response Formatting** - Return consistent, parseable movie data
4. **Performance Optimization** - Fast generation using local Llama 3.1 8B

## Architecture Flexibility

### Current Implementation: Ollama Llama 3.1 8B

```python
class LLMService:
    def __init__(self):
        self.base_url = f"http://{settings.EMBEDDING_HOST}:{settings.EMBEDDING_PORT}"
        self.model = "llama3.1:8b"  # Local Ollama model
```

### Future Model Options via Configuration

```python
# Could easily switch to:
if settings.LLM_PROVIDER == "anthropic":
    # Use Pydantic AI with Claude
    from pydantic_ai import Agent
    self.agent = Agent('claude-3-5-sonnet', ...)

elif settings.LLM_PROVIDER == "openai":
    # Use GPT-4/5 via OpenAI API
    self.client = openai.AsyncClient(...)

elif settings.LLM_PROVIDER == "ollama":
    # Current implementation
    self.base_url = f"http://{settings.EMBEDDING_HOST}:{settings.EMBEDDING_PORT}"
```

## Vector Context Integration

### Fast Vector Retrieval → Slow Generation Pattern

```python
async def generate_movie_recommendations(self, user_query: str, similar_preferences: List[Dict]):
    # FAST: Vector similarity search (sub-10ms)
    # similar_preferences already retrieved from Qdrant

    # FAST: Context preparation from vector results  
    context = self._prepare_context(user_query, similar_preferences)

    # SLOWER: LLM text generation (1-5 seconds)
    response = await self._call_ollama_chat(prompt)
```

**Performance Characteristics:**
- Vector Search: <10ms (Qdrant similarity search)
- Context Prep: <1ms (string formatting)
- LLM Generation: 1-5s (Llama 3.1 8B inference)

## Context Preparation from Vector Results

The service transforms Qdrant search results into structured context:

```python
def _prepare_context(self, user_query: str, similar_preferences: List[Dict]) -> str:
    context_parts = [
        f"User is asking for: '{user_query}'",
        "",
        "Based on their preference history:",
    ]

    for i, pref in enumerate(similar_preferences[:3], 1):  # Top 3 most similar
        similarity = pref.get('score', 0)  # Cosine similarity score
        content = pref.get('payload', {}).get('content', 'Unknown preference')
        metadata = pref.get('payload', {}).get('metadata', {})

        context_parts.append(f"{i}. \"{content}\" (similarity: {similarity:.3f})")

        # Include rich metadata from Pydantic AI extraction
        if 'genres' in metadata:
            context_parts.append(f"   - Genres: {metadata['genres']}")
        if 'themes' in metadata:
            context_parts.append(f"   - Themes: {metadata['themes']}")
```

## Core Recommendation Prompt

The prompt engineering leverages vector context for personalized recommendations:

```python
def _create_recommendation_prompt(self, context: str, limit: int) -> str:
    return f"""You are a sophisticated movie recommendation expert. Based on the user's current request and their preference history, recommend {limit} specific movies or TV shows.

{context}

Please recommend {limit} specific titles that match their preferences. For each recommendation, provide:
1. Title and year
2. Brief description (1-2 sentences)  
3. Why it matches their preferences (reference their history)
4. Confidence score (0.0-1.0)

Focus on quality recommendations that truly match their taste patterns. Be specific about titles, not just genres.

Format your response as a numbered list with clear structure."""
```

## Example RAG Flow

### Input
```
User Query: "thoughtful sci-fi tonight"
Similar Preferences from Qdrant:
1. "I like sci-fi, but with good characters" (similarity: 0.679)
2. "Something like Arrival but more upbeat" (similarity: 0.668)
3. "More like The Martian less like depressing Black Mirror" (similarity: 0.666)
```

### Generated Context
```
User is asking for: 'thoughtful sci-fi tonight'

Based on their preference history:
1. "I like sci-fi, but with good characters" (similarity: 0.679)
   - Themes: character_driven, primary
2. "Something like Arrival but more upbeat" (similarity: 0.668)
   - Genres: ['science fiction', 'drama']
   - Themes: ['first contact', 'communication', 'aliens']
   - Mood: upbeat, lighter
```

### Expected Output
```
1. Her (2013)
   A lonely writer develops a relationship with an AI. Matches your love of thoughtful sci-fi with strong character development, similar to Arrival's philosophical depth but with warmer emotional tone.
   Confidence: 0.92

2. The Martian (2015)
   An astronaut stranded on Mars uses science to survive. Perfect for your preference for upbeat, problem-solving sci-fi over darker Black Mirror-style content.
   Confidence: 0.89
```

## Model Configuration Strategy

This architecture allows seamless switching between models based on requirements:

- **Local/Privacy**: Ollama Llama 3.1 8B (current)
- **Quality/Sophistication**: Claude 3.5 Sonnet via Pydantic AI
- **Speed/Cost**: GPT-4o-mini via OpenAI
- **Cutting Edge**: GPT-5 or Claude Opus (future)

The vector context preparation and prompt engineering remain consistent across models.