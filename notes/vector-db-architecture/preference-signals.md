# Preference Signals & Chunking Strategy

## Key Insight: Natural Chunking
**FastEmbed is your text-to-vector converter, while each user preference is naturally its own "chunk" that gets embedded and stored.**

Unlike traditional RAG (splitting documents into chunks), suggest.watch treats each user preference/signal as a complete, meaningful unit that gets its own vector.

## Types of Preference Signals

### 1. Query Preferences
- "Something like Arrival but more upbeat"
- "I want a dark detective mystery on rainy London streets"
- "Need a comfort movie for Sunday afternoon"

### 2. Feedback Signals
- "Loved the philosophical themes but too slow"
- "Perfect pacing for a weeknight"
- "Great concept but the ending fell flat"

### 3. Context Preferences
- "Friday night needs something lighter"
- "Rainy day calls for cozy mysteries"
- "Post-work brain needs simple entertainment"

### 4. Mood-Based Signals
- "In the mood for something contemplative"
- "Need an adrenaline rush tonight"
- "Want to cry but in a good way"

### 5. Comparative Signals
- "Like Blade Runner but less depressing"
- "More Marvel, less DC darkness"
- "Pixar emotional depth without the kids' movie feel"

### 6. Time/Situation Context
- "Two-hour limit for weeknights"
- "Background viewing while cooking"
- "Full attention weekend movie experience"

### 7. Social Context
- "Date night appropriate"
- "Family-friendly but not boring for adults"
- "Solo viewing, can be weird/experimental"

### 8. Genre Refinement
- "Love sci-fi but hate space battles"
- "Horror without jump scares"
- "Comedy that's clever, not slapstick"

## Signal Storage Strategy
Each signal type gets stored with rich metadata:
- Signal type (query/feedback/context/mood/etc.)
- Emotional valence (positive/negative/neutral)
- Temporal context (time of day/week/season)
- Social context (solo/date/family/friends)
- Content specificity (genre/theme/style preferences)

This creates a rich preference landscape where vectors capture not just what you like, but when, why, and how you like it.