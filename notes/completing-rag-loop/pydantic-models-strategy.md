# Pydantic Models in LLM Integration: Structure vs. Flexibility

## Current Architecture Decision: Raw Text vs. Structured Output

### Why We're NOT Using Pydantic Models (Yet)

In the current LLMService, we're deliberately returning raw text instead of structured Pydantic models:

```python
def _parse_recommendation_response(self, response: str, user_query: str) -> Dict[str, Any]:
    """Parse Llama's response into structured format"""

    # For now, return the raw response with metadata
    # TODO: Could add more sophisticated parsing to extract structured data

    return {
        "user_query": user_query,
        "recommendations": response.strip(),  # Raw LLM text
        "model_used": self.model,
        "generation_method": "ollama_llama_3_1_8b",
        "status": "success"
    }
```

## When Pydantic Models Become Critical

### Option 1: Raw Text (Current Approach)

**Pros:**
- ✅ Flexible output - LLM can be creative with formatting
- ✅ Fast development - No complex parsing needed
- ✅ Human-readable - Great for CLI demonstration
- ✅ Model agnostic - Works with any text generation API

**Cons:**
- ❌ Inconsistent structure - Hard to programmatically process
- ❌ No validation - Could get malformed responses
- ❌ Integration challenges - Difficult to use in APIs/UIs

### Option 2: Pydantic Structured Output (Future Enhancement)

```python
from pydantic import BaseModel, Field
from typing import List

class MovieRecommendation(BaseModel):
    title: str = Field(..., description="Movie title with year")
    year: int = Field(..., description="Release year")
    description: str = Field(..., max_length=200, description="Brief movie description")
    reasoning: str = Field(..., description="Why this matches user preferences")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence")
    genres: List[str] = Field(default_factory=list)
    streaming_services: List[str] = Field(default_factory=list)

class RecommendationResponse(BaseModel):
    user_query: str
    recommendations: List[MovieRecommendation] = Field(..., min_items=1, max_items=6)
    context_used: str
    model_used: str
    generation_time_ms: float
```

## Why Pydantic Models Matter for Production

### 1. Data Validation & Consistency

```python
# With Pydantic, this would fail fast:
recommendation = MovieRecommendation(
    title="Her",
    year="twenty-thirteen",  # ❌ TypeError: int expected
    confidence=1.5           # ❌ ValidationError: must be <= 1.0
)
```

### 2. API Integration

```python
# FastAPI endpoint with guaranteed structure:
@router.post("/api/v1/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    result = await llm_service.generate_movie_recommendations(...)
    return result  # Automatically validated & serialized
```

### 3. LLM Prompt Engineering for Structure

```python
def _create_structured_prompt(self, context: str) -> str:
    return f"""Based on this context, return recommendations in this EXACT JSON format:

{context}

```json
{{
  "recommendations": [
    {{
      "title": "Movie Title",
      "year": 2023,
      "description": "Brief description here",
      "reasoning": "Why it matches their preferences",
      "confidence": 0.85,
      "genres": ["sci-fi", "drama"],
      "streaming_services": ["Netflix", "Prime"]
    }}
  ]
}}
```

Return valid JSON only, no other text."""
```

### 4. Error Handling & Fallbacks

```python
async def _parse_structured_response(self, response: str) -> RecommendationResponse:
    try:
        # Try to parse as structured JSON
        data = json.loads(response)
        return RecommendationResponse.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Failed to parse structured response: {e}")
        # Fallback to simpler parsing or retry
        return self._fallback_parse(response)
```

## Implementation Strategy

### Phase 1 (Current): Raw Text for Rapid Prototyping

- Get the RAG loop working end-to-end
- Focus on prompt engineering and context quality
- Perfect for CLI demonstrations and blog posts

### Phase 2 (Next): Structured Output with Pydantic

- Add MovieRecommendation and RecommendationResponse models
- Implement JSON-structured prompts
- Add validation and error handling

### Phase 3 (Future): Multi-Model Support

```python
# Different models, same structure:
if settings.LLM_PROVIDER == "anthropic":
    # Pydantic AI with built-in structured output
    agent = Agent('claude-3-5-sonnet', result_type=RecommendationResponse)

elif settings.LLM_PROVIDER == "openai":
    # OpenAI structured outputs with Pydantic
    response = await client.chat.completions.create(
        model="gpt-4",
        response_format={"type": "json_object"},
        messages=[...],
    )
```

## Key Insight: Progressive Structure

Start with flexible text (current) → Add optional structure → Enforce strict validation (production).

This lets us:
1. **Validate the RAG concept quickly**
2. **Refine prompts without structure constraints**
3. **Add structure when we know what works**
4. **Scale to production with consistent APIs**