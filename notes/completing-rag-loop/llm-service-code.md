# LLMService Implementation Code

## Core Service Class

```python
class LLMService:
    """Service for generating text responses using Ollama Llama models"""
    
    def __init__(self):
        self.base_url = f"http://{settings.EMBEDDING_HOST}:{settings.EMBEDDING_PORT}"
        self.model = "llama3.1:8b"  # Use Llama 3.1 8B for text generation
    
    async def generate_movie_recommendations(
        self, 
        user_query: str, 
        similar_preferences: List[Dict[str, Any]],
        limit: int = 4,
        streaming_callback=None
    ) -> Dict[str, Any]:
        """
        Generate movie recommendations based on user query and similar preferences
        
        Args:
            user_query: The user's current request (e.g., "thoughtful sci-fi tonight")
            similar_preferences: List of similar preferences from vector search
            limit: Number of movie recommendations to generate
            streaming_callback: Optional async function to call with each token for real-time display
            
        Returns:
            Dict containing movie recommendations with reasoning
        """
        
        # Prepare context from vector search results
        context = self._prepare_context(user_query, similar_preferences)
        
        # Create prompt for movie recommendations
        prompt = self._create_recommendation_prompt(context, limit)
        
        # Generate recommendations using Llama 3.1 8B with streaming
        response = await self._call_ollama_chat(prompt, streaming_callback)
        
        # Parse and structure the response
        return self._parse_recommendation_response(response, user_query)
```

## Prompt Engineering

```python
def _create_recommendation_prompt(self, context: str, limit: int) -> str:
    """Create the prompt for Llama 3.1 8B to generate movie recommendations"""
    
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

## Streaming Implementation

```python
async def _call_ollama_chat(self, prompt: str, streaming_callback=None) -> str:
    """Make streaming API call to Ollama for text generation"""
    
    try:
        full_response = ""
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,  # Enable streaming!
                    "options": {
                        "temperature": 0.7,  # Creative but coherent recommendations
                        "top_p": 0.9,        # Diverse vocabulary, avoid weird words
                        "top_k": 40,         # Focused vocabulary selection
                        "num_predict": 800,  # Enough for detailed recommendations
                    }
                },
                timeout=60.0
            ) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_lines():
                    if chunk.strip():  # Skip empty lines
                        try:
                            data = json.loads(chunk)
                            
                            if "response" in data:
                                token = data["response"]
                                full_response += token
                                
                                # Call streaming callback if provided (for real-time display)
                                if streaming_callback:
                                    await streaming_callback(token)
                            
                            # Check if generation is complete
                            if data.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            # Skip malformed JSON chunks
                            continue
        
        return full_response.strip()
            
    except Exception as e:
        logger.error(f"Ollama streaming text generation failed: {e}")
        raise Exception(f"Failed to generate recommendations: {str(e)}")
```

## Key Implementation Details

### Architecture Design
- **Model flexibility**: Easy to swap between different Ollama models
- **Streaming support**: Real-time token display via callback function
- **Error handling**: Graceful handling of malformed JSON chunks and network issues
- **Timeout protection**: 60-second timeout prevents hanging

### Parameter Tuning
- **temperature: 0.7** - Creative but coherent recommendations
- **top_p: 0.9** - Diverse vocabulary while avoiding weird words
- **top_k: 40** - Focused vocabulary selection
- **num_predict: 800** - Enough tokens for 4 detailed recommendations

### Streaming Benefits
- **Real-time display**: Users see text appearing as it's generated
- **Better perceived performance**: Feels faster than batch processing
- **Progressive engagement**: Keeps users engaged during generation
- **Error resilience**: Partial results if connection drops

This implementation completes the RAG loop by transforming vector similarity results into personalized, streaming movie recommendations using local Llama 3.1 8B inference.