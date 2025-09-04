
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

![AI robot tbd generating recommendations layer, turning search results into tailored recommendations.*

## Where We Left Off

In [Part 1](/posts/vector-databases-rag-pipeline/), we built the foundation of a movie recommendation RAG pipeline. We took raw user preferences, generated 1024-dimension vector embeddings using `bge-large`, and stored them in a Qdrant vector database. The result was a semantic search engine that could retrieve relevant preferences with impressive accuracy.

For example, searching for "thoughtful sci-fi tonight" surfaced:

1.  (Similarity: 0.679) "I like sci-fi, but with good characters..."
2.  (Similarity: 0.668) "Something like Arrival but more upbeat"
3.  (Similarity: 0.666) "More like The Martian less like depressing Black Mirror"

That’s the “Retrieval” in RAG. But that’s only half the story. The real challenge—and opportunity—comes next: *How do we turn this retrieved context into actual movie recommendations that fit what you’re in the mood for tonight?*

## Going Beyond Similar: Intent and Generation

`suggest.watch` isn’t just about finding what’s similar. The real value is letting you express what you’re looking for—how you want a movie to *feel* tonight—and combining that intent with your historical taste. Can a model use your query and context to generate recommendations that don’t just echo the past, but meet you in the moment?

This is where the “Generation” piece of RAG comes in. We want to synthesize—not just match—recommendations, along with clear reasoning tied to your actual preferences.

## Completing the Loop: Retrieval Plus Generation

Our refined pipeline makes each step clear and modular:

1. **Vector Search (Retrieval):** Queries go through Qdrant to surface the most relevant historical preferences based on semantic similarity.
2. **Context Preparation:** Retrieved preferences are formatted, including metadata, into structured prompts that capture both intent and taste.
3. **LLM Generation:** The local Llama 3.1 8B model reasons over this context to generate movie recommendations, referencing your current request and past preferences.

The retrieval and generation steps complement each other: fast semantic search for context, and careful generation for recommendations.

```bash
root@ollama-ai1:~# ollama list
NAME                ID              SIZE      MODIFIED      
bge-large:latest    b3d71c928059    670 MB
llama3.1:8b         46e0c10c039e    4.9 GB
```
*Both models run locally, keeping inference fast and private.*

## Streaming Output: A Better User Experience

Waiting several seconds for an AI response—especially with no feedback—can feel slow, or worse, broken. When the output arrives all at once, you have no sense of progress or anticipation.

With streaming, recommendations appear word by word as the LLM generates them; immediately, you can see that something is happening. Progress is visible. If an error occurs partway, you still get partial results. This small change makes the process feel much more like an ongoing conversation, not a delayed dump of information.

- **Immediate feedback:** See right away that your query is being processed
- **Progressive engagement:** Recommendations unfold in real time
- **Error resilience:** Partial output is available even if not everything completes

Here’s how that looks in practice:
```python
async def _call_ollama_chat(self, prompt: str, streaming_callback=None) -> str:
    full_response = ""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": True,  # Streaming enabled
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
                        if streaming_callback:
                            await streaming_callback(token)
    return full_response.strip()
```

A `streaming_callback` (like just printing each token to the console) allows you to see the model “think” in real-time—as new words are generated, they appear for the user.

## Designing Useful Prompts

Everything depends on giving the model the right information, in the right format. Our prompts are constructed to combine the “what you want now” intent with your most relevant history:

```python
def _prepare_context(self, user_query: str, similar_preferences: List[Dict]) -> str:
    context_parts = [
        f"User is asking for: '{user_query}'",
        "",
        "Based on their preference history:",
    ]
    for i, pref in enumerate(similar_preferences[:3], 1):
        similarity = pref.get('score', 0)
        content = pref.get('payload', {}).get('content', 'Unknown preference')
        context_parts.append(f"{i}. \"{content}\" (similarity: {similarity:.3f})")
    return "\n".join(context_parts)
```

This prep step ensures the model gets concrete examples, not vague lists—“Make recommendations that reflect my request *and* my track record.”

The prompt then asks for specific, justified recommendations:

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

## In Action: The Complete RAG Pipeline

Running the live CLI demo, the results (streaming as they generate) look like this:

```
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

1. Sunshine (2007)
   Description: A team of astronauts embarks on a mission to reignite the sun after it begins to die, facing personal struggles and existential questions along the way.
   Why it matches: Like "Arrival," "Sunshine" explores themes of first contact, but balances action and emotional depth, and focuses on character development (similarity: 0.724).
   Confidence score: 0.855

2. Another Earth (2011)
   Description: When a duplicate Earth appears in the sky, a woman discovers she may have an identical twin, leading to questions about identity and connection.
   Why it matches: Focuses on character-driven storytelling and complex themes; tone is more upbeat than typical sci-fi, a fit for the user's historic preferences (similarity: 0.753).
   Confidence score: 0.832

3. Passengers (2016)
   Description: Two spaceship passengers wake too early and must navigate feelings for each other while trying to save the ship.
   Why it matches: Combines character-driven storytelling and communication themes with an upbeat, romantic tone, in line with the user's preference (similarity: 0.728).
   Confidence score: 0.819

4. Europa Report (2013)
   Description: Astronauts explore Jupiter’s moon Europa in search of life, confronting discoveries that challenge their worldview.
   Why it matches: Like "Sunshine," focuses on character, has an upbeat tone, and explores first contact (similarity: 0.739).
   Confidence score: 0.805

Each recommendation explains *why* it fits, referring back to the actual semantic content of your stored preferences—not just general genre tags.

## Why the User Experience Feels Right

- **Streaming output** keeps things responsive and engaging.
- **Justified recommendations** let you understand why these movies, not just what they are.
- **Local inference** (Ollama + Qdrant) ensures your preferences and recommendations remain private, fast, and modifiable.

## Settings That Strive for Quality

Tuning LLM generation is all about balancing creativity and precision. The parameters for this pipeline:
```
"temperature": 0.7,    # Some creativity, not wild
"top_p": 0.9,          # Broad enough, avoids oddities
"num_predict": 800,    # Detailed, not abrupt
"top_k": 40            # Focused vocabulary
```

This hits a sweet spot: interesting suggestions, but all strongly guided by context and history.

## The Foundation for Future Improvements

The current CLI and architecture are designed for flexibility. As the system matures toward production:
- *Structured outputs* (e.g., via Pydantic models) can be enforced for API reliability.
- Prompt strategy and model can be updated without major rewrites.
- Reranking, genre filters, and even streaming service integration become straightforward next steps.

## Wrapping Up: What’s Accomplished and What’s Next

Over these two posts, we’ve built a pipeline that’s:
- **Retrieval-augmented:** Semantic search gets you immediately relevant context from your own evolving history.
- **Intent-aware:** Allows you to specify what kind of movie you want tonight—not just what’s similar.
- **Reasoned:** Model recommendations are grounded in your history, not just genre overlap.
- **Engaging:** Streaming output keeps the experience lively and user-centered.

In the next post we'll look at ways to improve quality even further: reranking, additional metadata, and coping with ambiguity for even better recommendations.

---

If you’re curious about deeper implementation details, parameter trade-offs, or the move from raw text to structured API outputs, see the [attached technical notes] and stay tuned for future posts.

---

*Questions or feedback? Let me know below, or follow along for more practical AI system builds.*

---

