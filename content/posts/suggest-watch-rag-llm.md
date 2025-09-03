---
title: "Completing the RAG Loop: From Vector Search to LLM Recommendations - Part 2"
date: 2025-09-04T09:00:00-00:00
draft: true
tags: ["AI", "RAG", "LLM", "Llama3", "Ollama", "Pydantic", "FastAPI", "suggest.watch"]
categories: ["ai-architecture", "hands-on-guide"]
description: "Part 2: Taking vector search results and using a local LLM to generate personalized, streaming movie recommendations, completing our RAG pipeline."
author: "Mark Holton"
cover:
    image: "/images/markbot-tbd.jpg"
    alt: "AI robot refining a list of items, symbolizing an LLM reranking and generating recommendations"
    caption: "The LLM acts as the final reasoning layer, turning search results into tailored recommendations."
---

![AI robot tbd generating recommendations](/images/markbot-tbd.jpg)
*The LLM acts as the final reasoning layer, turning search results into tailored recommendations.*

## Where We Left Off

In [Part 1](/posts/vector-databases-rag-pipeline/), we built the foundation of a movie recommendation RAG pipeline. We took raw user preferences, generated 1024-dimension vector embeddings using `bge-large`, and stored them in a Qdrant vector database. The result was a powerful semantic search engine that could find similar preferences with impressive accuracy.

When we searched for "thoughtful sci-fi tonight," we got back a ranked list of our own stored preferences:

1.  (Similarity: 0.679) "I like sci-fi, but with good characters..."
2.  (Similarity: 0.668) "Something like Arrival but more upbeat"
3.  (Similarity: 0.666) "More like The Martian less like depressing Black Mirror"

This is the "Retrieval" part of RAG. It's fast, efficient, and semantically intelligent. But it leaves us with a critical question: *How do we turn this retrieved context into actual movie recommendations?*

This is where the "Generation" part comes in. In this post, we'll complete the loop by building a service that feeds these search results to a Large Language Model (LLM) to generate personalized, well-reasoned movie suggestions.

## Completing the RAG Architecture

Our existing pipeline was fast and effective at retrieval. Now, we're adding the final reasoning layer. The complete architecture looks like this:

![RAG movie pipeline with LLM generation](/images/tbd2.png)
*The complete RAG pipeline: Vector search retrieves relevant context, which is then passed to an LLM for recommendation generation.*

The flow is a classic "fast retrieval, slow generation" pattern:

1.  **Vector Search (Fast):** The user's query is embedded and sent to Qdrant, which returns a list of semantically similar preferences in milliseconds.
2.  **Context Preparation (Fast):** The raw text and metadata from the search results are formatted into a clear, structured prompt for the LLM.
3.  **LLM Generation (Slower):** The prompt, rich with user-specific context, is sent to our locally-run **Llama 3.1 8B** model via Ollama. The LLM then reasons over this context to generate movie recommendations.

For this entire pipeline, I'm using a local AI stack. Both the `bge-large` embedding model that we explored in Part 1 and the `llama3.1:8b` generative model are running in the same Ollama container, ensuring privacy and performance with no external API calls.

```bash
root@ollama-ai1:~# ollama list
NAME                ID              SIZE      MODIFIED      
bge-large:latest    b3d71c928059    670 MB    ...    
llama3.1:8b         46e0c10c039e    4.9 GB    ... 
```

## The Magic of Streaming: Real-Time Recommendations

Before diving into the code, let's talk about user experience. Waiting several seconds for a model to generate a response can make an application feel slow or broken. The solution is **streaming**.

Instead of waiting for the full response, we process it token-by-token as the LLM generates it. This makes the recommendations appear on screen word-by-word, creating a dynamic and engaging experience that feels like the AI is "thinking" through its suggestions in real time.

Here’s how we implement it in our service using `httpx`:

```python
# In our LLMService, we use a streaming request to Ollama
async def _call_ollama_chat(self, prompt: str, streaming_callback=None) -> str:
    full_response = ""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": True,  # This is the key!
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 800,
                }
            },
            timeout=60.0
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_lines():
                if chunk.strip():
                    data = json.loads(chunk)
                    if "response" in data:
                        token = data["response"]
                        full_response += token
                        
                        # If a callback is provided, send the token for live display
                        if streaming_callback:
                            await streaming_callback(token)
    return full_response.strip()
```

When we call our service, we pass a simple callback function that prints each token to the console. This small change transforms the user experience from a static wait to a live, conversational interaction.

## Building the Recommendation Prompt

The quality of an LLM's output depends heavily on the quality of its prompt. Our goal is to give the model all the context it needs to act like a movie expert. We combine the user's immediate query with the rich history retrieved from our vector database.

```python
def _prepare_context(self, user_query: str, similar_preferences: List[Dict]) -> str:
    """Formats Qdrant search results into a structured context for the LLM."""
    context_parts = [
        f"User is asking for: '{user_query}'",
        "",
        "Based on their preference history:",
    ]

    # Add the top 3 most similar preferences from our vector search
    for i, pref in enumerate(similar_preferences[:3], 1):
        similarity = pref.get('score', 0)
        content = pref.get('payload', {}).get('content', 'Unknown preference')
        context_parts.append(f"{i}. "{content}" (similarity: {similarity:.3f})")

    return "\n".join(context_parts)

def _create_recommendation_prompt(self, context: str, limit: int) -> str:
    """Creates the final prompt instructing the LLM on its task."""
    return f"""You are a sophisticated movie recommendation expert. Based on the user's current request and their preference history, recommend {limit} specific movies or TV shows.

{context}

Please recommend {limit} specific titles that match their preferences. For each recommendation, provide:
1. Title and year
2. Brief description (1-2 sentences)  
3. Why it matches their preferences (reference their history)
4. Confidence score (0.0-1.0)

Format your response as a numbered list with clear structure."""
```

This prompt engineering guides the LLM to not only suggest movies but also to *explain its reasoning* by referencing the user's own stated preferences, creating a truly personalized and transparent recommendation.

## The Complete RAG Pipeline in Action

Now, let's run the full pipeline. We'll execute the same search as before, but this time, the retrieved context will be passed to Llama 3.1 for generation.

```bash
> search thoughtful sci-fi tonight
🔍 Searching for: 'thoughtful sci-fi tonight'
🔢 Generating query embedding with bge-large...
🎯 Searching Qdrant for similar preferences...
🎉 Found 3 similar preferences:

#1 (Similarity: 0.679)
   💬 "I like sci-fi, but with good characters, it can't be just about the nerdy sets"
#2 (Similarity: 0.668)
   💬 "Something like Arrival but more upbeat"
#3 (Similarity: 0.666)
   💬 "More like The Martian less like depressing Black Mirror"

🎬 Generating movie recommendations with Llama 3.1 8B...

Based on the user's preference history, I've curated four thoughtful sci-fi movie recommendations that meet their requirements:

**1.** **"Sunshine" (2007)**

Description: A team of astronauts embarks on a mission to reignite the sun after it begins to die, facing personal struggles and existential questions along the way.

Why it matches their preferences: Like "Arrival," "Sunshine" explores themes of first contact and communication with an alien entity. The movie also has an upbeat tone, balancing action and emotional depth. Additionally, its focus on character development and relationships echoes the user's preference for good characters over nerdy sets.

Confidence score: 0.855

**2.** **"Another Earth" (2011)**

Description: When a duplicate Earth appears in the sky, a young woman discovers that she has an identical twin on the new planet, leading to questions about identity and human connection.

Why it matches their preferences: This film shares similarities with "The Martian" by focusing on character-driven storytelling and exploring complex themes. Its tone is also more upbeat than typical sci-fi fare, making it a suitable match for the user's preference.

Confidence score: 0.832

**3.** **"Passengers" (2016)**

Description: Two passengers on a spaceship wake up 90 years too early and must navigate their feelings for each other while trying to save the ship from destruction.

Why it matches their preferences: This movie combines elements of "Arrival" by exploring first contact and communication, but with a more romantic and upbeat tone. Its focus on character development and relationships also aligns with the user's preference.

Confidence score: 0.819

**4.** **"Europa Report" (2013)**

Description: A team of astronauts embarks on a mission to one of Jupiter's moons, Europa, where they discover signs of life and must confront the implications of this discovery.

Why it matches their preferences: Like "Sunshine," "Europa Report" has an upbeat tone and focuses on character development and relationships. The movie also explores themes of first contact and communication with an alien entity.

Confidence score: 0.805

✅ Recommendations generated successfully!
🤖 Model used: llama3.1:8b
```

The output streams in just like this, word by word. The result is a set of pretty high-quality, actionable recommendations, each with a clear explanation tying it back to the user's specific tastes. The LLM successfully synthesized the context—"thoughtful," "good characters," "upbeat," "like The Martian"—to generate a relevant and personalized list.

## The RAG Loop is Complete

Over these two posts, we have built a complete, end-to-end RAG pipeline from scratch:

-   ✅ **Semantic Storage:** Captured user preferences as 1024-dimensional vectors in Qdrant.
-   ✅ **Intelligent Retrieval:** Used cosine similarity to find the most relevant preferences for any given query.
-   ✅ **Contextual Generation:** Fed the retrieved context to a local LLM (Llama 3.1) to reason and generate recommendations.
-   ✅ **Streaming CLI:** Used streaming to provide a real-time, conversational experience. When we build the front end, we will carry this through

This architecture gives us the best of both worlds: the speed and precision of vector search, combined with the reasoning and generative power of a large language model. Together, they create a system that understands not just *what* you like, but *why* you like it, and can help you discover your next favorite movie.

```